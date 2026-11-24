/* ============================================================
   ACTUALIZACIÓN PARA AUTENTICACIÓN, COMPRAS, VENTAS, KARDEX Y ALERTAS

   Importa este archivo en la base indicada en DB_NAME, después de
   Script.sql y de BD/procedimientos_almacenados.sql.
   Se puede ejecutar más de una vez: no duplica registros.
   ============================================================ */


/* ============================================================
   1. STOCK BAJO CUANDO stock_actual <= stock_minimo
   La especificación funcional define el stock bajo con <=.
   Agotado (0) tiene prioridad sobre stock bajo.
   ============================================================ */

CREATE OR REPLACE VIEW vw_inventario_general AS
SELECT
    i.id_inventario,
    p.codigo_barras,
    p.nombre AS producto,
    c.nombre AS categoria,
    s.nombre AS sucursal,
    i.stock_actual,
    i.stock_minimo,
    i.stock_maximo,
    CASE
        WHEN i.stock_actual = 0 THEN 'AGOTADO'
        WHEN i.stock_actual <= i.stock_minimo THEN 'STOCK BAJO'
        WHEN i.stock_actual > i.stock_maximo THEN 'SOBRESTOCK'
        ELSE 'NORMAL'
    END AS estado_inventario,
    i.ubicacion,
    i.fecha_actualizacion
FROM inventario i
INNER JOIN productos p ON i.id_producto = p.id_producto
INNER JOIN categorias c ON p.id_categoria = c.id_categoria
INNER JOIN sucursales s ON i.id_sucursal = s.id_sucursal;


/* ============================================================
   2. CLIENTE GENÉRICO PARA VENTAS SIN DATOS DEL COMPRADOR
   ============================================================ */

INSERT INTO clientes (tipo_documento, numero_documento, nombre, apellido)
SELECT 'CC', '222222222222', 'Consumidor final', NULL
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM clientes WHERE numero_documento = '222222222222'
);


/* ============================================================
   3. INVENTARIO EN CERO PARA CADA PRODUCTO ACTIVO Y SUCURSAL ACTIVA
   Los datos de ejemplo no tienen inventario en Sucursal Sur. Se crea
   igual que lo hace sp_crear_producto: saldo 0 y límites del producto.
   ============================================================ */

INSERT INTO inventario (id_producto, id_sucursal, stock_actual, stock_minimo, stock_maximo)
SELECT p.id_producto, s.id_sucursal, 0, p.stock_minimo, p.stock_maximo
FROM productos p
CROSS JOIN sucursales s
WHERE p.estado = 1
  AND s.estado = 1
  AND NOT EXISTS (
      SELECT 1 FROM inventario i
      WHERE i.id_producto = p.id_producto AND i.id_sucursal = s.id_sucursal
  );


/* ============================================================
   4. ALERTAS DE INVENTARIO
   Una sola regla para la carga inicial y para cada cambio de stock.
   NULL en un parámetro significa "todos".
   ============================================================ */

DROP PROCEDURE IF EXISTS sp_sincronizar_alertas;

DELIMITER $$

CREATE PROCEDURE sp_sincronizar_alertas(
    IN p_id_producto INT,
    IN p_id_sucursal INT
)
SQL SECURITY INVOKER
MODIFIES SQL DATA
BEGIN
    -- Cierra las alertas pendientes que ya no corresponden a la situación actual.
    UPDATE alertas_inventario a
    INNER JOIN inventario i ON i.id_producto = a.id_producto AND i.id_sucursal = a.id_sucursal
    INNER JOIN productos p ON p.id_producto = i.id_producto
    INNER JOIN sucursales s ON s.id_sucursal = i.id_sucursal
    SET a.estado = 'ATENDIDA'
    WHERE a.estado = 'PENDIENTE'
      AND (p_id_producto IS NULL OR a.id_producto = p_id_producto)
      AND (p_id_sucursal IS NULL OR a.id_sucursal = p_id_sucursal)
      AND a.tipo_alerta <> CASE
              WHEN p.estado <> 1 OR s.estado <> 1 THEN 'NINGUNA'
              WHEN i.stock_actual = 0 THEN 'PRODUCTO_AGOTADO'
              WHEN i.stock_actual <= i.stock_minimo THEN 'STOCK_BAJO'
              WHEN i.stock_actual > i.stock_maximo THEN 'SOBRESTOCK'
              ELSE 'NINGUNA'
          END;

    -- Crea la alerta pendiente que falte, sin duplicar el mismo tipo.
    INSERT INTO alertas_inventario (id_producto, id_sucursal, tipo_alerta, mensaje)
    SELECT
        x.id_producto,
        x.id_sucursal,
        x.tipo_alerta,
        LEFT(CONCAT(
            'El producto ', x.producto,
            CASE x.tipo_alerta
                WHEN 'PRODUCTO_AGOTADO' THEN ' está agotado en '
                WHEN 'STOCK_BAJO' THEN ' quedó con stock bajo en '
                ELSE ' superó el stock máximo en '
            END,
            x.sucursal, '.'
        ), 300)
    FROM (
        SELECT
            i.id_producto,
            i.id_sucursal,
            p.nombre AS producto,
            s.nombre AS sucursal,
            CASE
                WHEN i.stock_actual = 0 THEN 'PRODUCTO_AGOTADO'
                WHEN i.stock_actual <= i.stock_minimo THEN 'STOCK_BAJO'
                WHEN i.stock_actual > i.stock_maximo THEN 'SOBRESTOCK'
            END AS tipo_alerta
        FROM inventario i
        INNER JOIN productos p ON p.id_producto = i.id_producto
        INNER JOIN sucursales s ON s.id_sucursal = i.id_sucursal
        WHERE p.estado = 1
          AND s.estado = 1
          AND (p_id_producto IS NULL OR i.id_producto = p_id_producto)
          AND (p_id_sucursal IS NULL OR i.id_sucursal = p_id_sucursal)
    ) AS x
    WHERE x.tipo_alerta IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM alertas_inventario a
          WHERE a.id_producto = x.id_producto
            AND a.id_sucursal = x.id_sucursal
            AND a.tipo_alerta = x.tipo_alerta
            AND a.estado = 'PENDIENTE'
      );
END$$

DELIMITER ;


/* ============================================================
   5. CARGA INICIAL DE ALERTAS
   ============================================================ */

CALL sp_sincronizar_alertas(NULL, NULL);
