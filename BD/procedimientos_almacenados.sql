-- Selecciona primero la base configurada en DB_NAME.
-- Las rutinas de escritura participan en la transacción del llamador.
-- Desde SQL, ejecuta START TRANSACTION antes del CALL y COMMIT o ROLLBACK después.

DROP PROCEDURE IF EXISTS sp_crear_producto;
DROP PROCEDURE IF EXISTS sp_registrar_movimiento_inventario;
DROP PROCEDURE IF EXISTS sp_consultar_kardex;

DELIMITER $$

CREATE PROCEDURE sp_crear_producto(
    IN p_id_categoria INT,
    IN p_codigo_barras VARCHAR(50),
    IN p_nombre VARCHAR(150),
    IN p_descripcion VARCHAR(300),
    IN p_marca VARCHAR(100),
    IN p_unidad_medida VARCHAR(30),
    IN p_precio_compra DECIMAL(12,2),
    IN p_precio_venta DECIMAL(12,2),
    IN p_stock_minimo INT,
    IN p_stock_maximo INT
)
SQL SECURITY INVOKER
MODIFIES SQL DATA
BEGIN
    DECLARE v_categoria_activa TINYINT DEFAULT NULL;
    DECLARE v_id_producto INT;

    SELECT estado INTO v_categoria_activa
    FROM categorias WHERE id_categoria = p_id_categoria
    FOR UPDATE;

    IF COALESCE(v_categoria_activa, 0) <> 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MYSQL_ERRNO = 30001, MESSAGE_TEXT = 'Selecciona una categoría activa.';
    END IF;

    IF COALESCE(TRIM(p_codigo_barras), '') = ''
        OR COALESCE(TRIM(p_nombre), '') = ''
        OR COALESCE(TRIM(p_unidad_medida), '') = '' THEN
        SIGNAL SQLSTATE '45000'
            SET MYSQL_ERRNO = 30002,
                MESSAGE_TEXT = 'Código de barras, nombre y unidad de medida son obligatorios.';
    END IF;

    INSERT INTO productos (
        id_categoria, codigo_barras, nombre, descripcion, marca, unidad_medida,
        precio_compra, precio_venta, stock_minimo, stock_maximo
    ) VALUES (
        p_id_categoria, p_codigo_barras, p_nombre, p_descripcion, p_marca, p_unidad_medida,
        p_precio_compra, p_precio_venta, p_stock_minimo, p_stock_maximo
    );

    SET v_id_producto = LAST_INSERT_ID();

    INSERT INTO inventario (id_producto, id_sucursal, stock_actual, stock_minimo, stock_maximo)
    SELECT v_id_producto, id_sucursal, 0, p_stock_minimo, p_stock_maximo
    FROM sucursales
    WHERE estado = 1;

    SELECT v_id_producto AS id_producto;
END$$

CREATE PROCEDURE sp_registrar_movimiento_inventario(
    IN p_id_producto INT,
    IN p_id_sucursal INT,
    IN p_id_tipo_movimiento INT,
    IN p_id_usuario INT,
    IN p_cantidad INT,
    IN p_referencia VARCHAR(100),
    IN p_observacion VARCHAR(300)
)
SQL SECURITY INVOKER
MODIFIES SQL DATA
BEGIN
    DECLARE v_producto_activo TINYINT DEFAULT NULL;
    DECLARE v_sucursal_activa TINYINT DEFAULT NULL;
    DECLARE v_usuario_activo TINYINT DEFAULT NULL;
    DECLARE v_tipo VARCHAR(7) DEFAULT NULL;
    DECLARE v_stock_anterior INT DEFAULT NULL;
    DECLARE v_stock_nuevo BIGINT;

    IF p_cantidad IS NULL OR p_cantidad <= 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MYSQL_ERRNO = 30003, MESSAGE_TEXT = 'La cantidad debe ser mayor que cero.';
    END IF;

    -- El bloqueo del producto también coordina este cambio con su desactivación.
    SELECT estado INTO v_producto_activo
    FROM productos WHERE id_producto = p_id_producto
    FOR UPDATE;

    IF COALESCE(v_producto_activo, 0) <> 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MYSQL_ERRNO = 30004, MESSAGE_TEXT = 'El producto debe existir y estar activo.';
    END IF;

    SELECT estado INTO v_sucursal_activa
    FROM sucursales WHERE id_sucursal = p_id_sucursal
    LOCK IN SHARE MODE;

    IF COALESCE(v_sucursal_activa, 0) <> 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MYSQL_ERRNO = 30005, MESSAGE_TEXT = 'La sucursal debe existir y estar activa.';
    END IF;

    SELECT estado INTO v_usuario_activo
    FROM usuarios WHERE id_usuario = p_id_usuario
    LOCK IN SHARE MODE;

    IF COALESCE(v_usuario_activo, 0) <> 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MYSQL_ERRNO = 30006, MESSAGE_TEXT = 'El usuario debe existir y estar activo.';
    END IF;

    SELECT tipo INTO v_tipo
    FROM tipos_movimiento WHERE id_tipo_movimiento = p_id_tipo_movimiento AND estado = 1
    LOCK IN SHARE MODE;

    IF v_tipo IS NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MYSQL_ERRNO = 30007, MESSAGE_TEXT = 'El tipo de movimiento debe existir y estar activo.';
    END IF;

    SELECT stock_actual INTO v_stock_anterior
    FROM inventario WHERE id_producto = p_id_producto AND id_sucursal = p_id_sucursal
    FOR UPDATE;

    IF v_stock_anterior IS NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MYSQL_ERRNO = 30008, MESSAGE_TEXT = 'El producto no tiene inventario en esta sucursal.';
    END IF;

    SET v_stock_nuevo = v_stock_anterior + IF(v_tipo = 'ENTRADA', p_cantidad, -p_cantidad);

    IF v_stock_nuevo < 0 OR v_stock_nuevo > 2147483647 THEN
        SIGNAL SQLSTATE '45000'
            SET MYSQL_ERRNO = 30009, MESSAGE_TEXT = 'El movimiento dejaría el saldo fuera del rango permitido.';
    END IF;

    INSERT INTO movimientos_inventario (
        id_producto, id_sucursal, id_tipo_movimiento, id_usuario, cantidad,
        stock_anterior, stock_nuevo, referencia, observacion
    ) VALUES (
        p_id_producto, p_id_sucursal, p_id_tipo_movimiento, p_id_usuario, p_cantidad,
        v_stock_anterior, v_stock_nuevo, p_referencia, p_observacion
    );

    UPDATE inventario
    SET stock_actual = v_stock_nuevo
    WHERE id_producto = p_id_producto AND id_sucursal = p_id_sucursal;

    SELECT LAST_INSERT_ID() AS id_movimiento,
           v_stock_anterior AS stock_anterior,
           v_stock_nuevo AS stock_nuevo;
END$$

CREATE PROCEDURE sp_consultar_kardex(
    IN p_id_producto INT,
    IN p_id_sucursal INT,
    IN p_desde DATETIME,
    IN p_hasta_exclusivo DATETIME
)
SQL SECURITY INVOKER
READS SQL DATA
BEGIN
    IF p_desde IS NOT NULL AND p_hasta_exclusivo IS NOT NULL AND p_desde >= p_hasta_exclusivo THEN
        SIGNAL SQLSTATE '45000'
            SET MYSQL_ERRNO = 30010, MESSAGE_TEXT = 'La fecha final debe ser posterior a la inicial.';
    END IF;

    SELECT k.*
    FROM movimientos_inventario AS m
    INNER JOIN vw_kardex AS k ON k.id_movimiento = m.id_movimiento
    WHERE (p_id_producto IS NULL OR m.id_producto = p_id_producto)
      AND (p_id_sucursal IS NULL OR m.id_sucursal = p_id_sucursal)
      AND (p_desde IS NULL OR m.fecha_movimiento >= p_desde)
      AND (p_hasta_exclusivo IS NULL OR m.fecha_movimiento < p_hasta_exclusivo)
    ORDER BY k.fecha_movimiento DESC, k.id_movimiento DESC;
END$$

DELIMITER ;

