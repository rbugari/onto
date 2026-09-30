-- ERP operativo (MariaDB). Export de estructura: mysqldump --no-data erp_distribuidora
-- Datos sinteticos. Solo se usa la estructura.

CREATE TABLE `clientes` (
  `id_cliente` int(11) NOT NULL AUTO_INCREMENT,
  `razon_social` varchar(200) NOT NULL,
  `cuit` varchar(13) DEFAULT NULL,
  `zona` varchar(50) DEFAULT NULL,
  `condicion_pago` varchar(30) DEFAULT NULL,
  `fecha_alta` date DEFAULT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id_cliente`),
  KEY `idx_clientes_zona` (`zona`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `productos` (
  `id_producto` int(11) NOT NULL AUTO_INCREMENT,
  `descripcion` varchar(200) NOT NULL,
  `rubro` varchar(60) DEFAULT NULL,
  `precio_lista` decimal(12,2) DEFAULT NULL,
  `unidad_medida` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`id_producto`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `pedidos` (
  `id_pedido` int(11) NOT NULL AUTO_INCREMENT,
  `id_cliente` int(11) NOT NULL,
  `fecha` datetime NOT NULL,
  `estado` varchar(20) NOT NULL COMMENT 'PENDIENTE, FACTURADO, ANULADO',
  `total` decimal(14,2) DEFAULT NULL,
  `id_vendedor` int(11) DEFAULT NULL,
  PRIMARY KEY (`id_pedido`),
  KEY `fk_pedidos_cliente` (`id_cliente`),
  CONSTRAINT `fk_pedidos_cliente` FOREIGN KEY (`id_cliente`) REFERENCES `clientes` (`id_cliente`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `pedido_items` (
  `id_pedido` int(11) NOT NULL,
  `renglon` int(11) NOT NULL,
  `id_producto` int(11) NOT NULL,
  `cantidad` decimal(12,3) NOT NULL,
  `precio_unitario` decimal(12,2) NOT NULL,
  `descuento` decimal(5,2) DEFAULT 0.00,
  PRIMARY KEY (`id_pedido`, `renglon`),
  CONSTRAINT `fk_items_pedido` FOREIGN KEY (`id_pedido`) REFERENCES `pedidos` (`id_pedido`),
  CONSTRAINT `fk_items_producto` FOREIGN KEY (`id_producto`) REFERENCES `productos` (`id_producto`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `stock_depositos` (
  `id_producto` int(11) NOT NULL,
  `deposito` varchar(20) NOT NULL,
  `stock_actual` decimal(12,3) NOT NULL,
  `actualizado` datetime DEFAULT NULL,
  PRIMARY KEY (`id_producto`, `deposito`),
  CONSTRAINT `fk_stock_producto` FOREIGN KEY (`id_producto`) REFERENCES `productos` (`id_producto`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
