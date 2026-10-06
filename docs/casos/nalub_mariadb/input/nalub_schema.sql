-- Esquema MariaDB de Nalub (solo estructura, sin datos), extraido del backup 2026-04-02.

CREATE TABLE IF NOT EXISTS `aplicapagos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `idpago` int(11) NOT NULL,
  `idpedido` int(11) NOT NULL,
  `idcliente` int(11) NOT NULL,
  `fecha` datetime NOT NULL,
  `importe` decimal(16,2) NOT NULL,
  `saldo` decimal(16,2) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idpago` (`idpago`),
  KEY `idpedido` (`idpedido`),
  KEY `idcliente` (`idcliente`),
  CONSTRAINT `aplicapagos_ibfk_1` FOREIGN KEY (`idpago`) REFERENCES `pagos` (`id`) ON DELETE NO ACTION,
  CONSTRAINT `aplicapagos_ibfk_2` FOREIGN KEY (`idpedido`) REFERENCES `pedidos` (`id`) ON DELETE NO ACTION,
  CONSTRAINT `aplicapagos_ibfk_3` FOREIGN KEY (`idcliente`) REFERENCES `clientes` (`id`) ON DELETE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=65061 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `CatClientes` (
  `CatCodigo` char(3) NOT NULL,
  `CatNombre` varchar(50) NOT NULL,
  PRIMARY KEY (`CatCodigo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `clientes` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(200) NOT NULL,
  `razonSocial` varchar(200) NOT NULL,
  `cuit` varchar(15) NOT NULL,
  `domicilio` varchar(200) NOT NULL,
  `entre` varchar(200) NOT NULL,
  `localidad` varchar(200) NOT NULL,
  `codpostal` varchar(10) NOT NULL,
  `horario` varchar(50) NOT NULL,
  `nomContacto` varchar(100) NOT NULL,
  `TE` varchar(20) NOT NULL,
  `Celular` varchar(20) NOT NULL,
  `email` varchar(100) NOT NULL,
  `fechaAlta` date NOT NULL,
  `deuda` decimal(15,2) NOT NULL,
  `fechaUltimoMov` date DEFAULT NULL,
  `fechaUltimoPago` date DEFAULT NULL,
  `tipoIva` int(11) DEFAULT NULL,
  `comentarios` text NOT NULL,
  `vendedor` int(11) NOT NULL,
  `CatCliente` char(3) DEFAULT NULL,
  `usuario` varchar(50) DEFAULT NULL,
  `pwd` varchar(100) DEFAULT NULL,
  `idSecundario` int(11) DEFAULT NULL,
  `porcentaje1` decimal(10,2) DEFAULT NULL,
  `porcentaje2` decimal(10,2) DEFAULT NULL,
  `porcentaje3` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `tipoIva` (`tipoIva`),
  KEY `vendedor` (`vendedor`),
  KEY `clientes_ibfk_3` (`CatCliente`) USING BTREE,
  CONSTRAINT `clientes_ibfk_1` FOREIGN KEY (`tipoIva`) REFERENCES `tipoIva` (`id`) ON DELETE NO ACTION,
  CONSTRAINT `clientes_ibfk_2` FOREIGN KEY (`vendedor`) REFERENCES `vendedores` (`id`) ON DELETE NO ACTION,
  CONSTRAINT `clientes_ibfk_3` FOREIGN KEY (`CatCliente`) REFERENCES `CatClientes` (`CatCodigo`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=2014 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `Deuda` (
  `Código` int(10) DEFAULT NULL,
  `Cliente` varchar(255) DEFAULT NULL,
  `Deuda` decimal(10,2) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `Deuda2` (
  `Cod` int(10) DEFAULT NULL,
  `Nombre` varchar(255) DEFAULT NULL,
  `Deuda` decimal(10,2) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `envases` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `litros` decimal(10,4) NOT NULL,
  `tipoenvaseid` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `tipoenvaseid` (`tipoenvaseid`),
  CONSTRAINT `envases_ibfk_1` FOREIGN KEY (`tipoenvaseid`) REFERENCES `tipoEnvase` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=46 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `ingStock` (
  `IngStockId` int(11) NOT NULL AUTO_INCREMENT,
  `ProveedorId` int(11) NOT NULL,
  `NroComprobante` varchar(30) NOT NULL,
  `IngStockFecha` date NOT NULL,
  `IngStockMonto` decimal(16,2) NOT NULL,
  `IngStockUnidades` int(11) NOT NULL,
  PRIMARY KEY (`IngStockId`),
  KEY `ProveedorId` (`ProveedorId`)
) ENGINE=InnoDB AUTO_INCREMENT=1178 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `ingStockItems` (
  `IngStockItemsId` int(11) NOT NULL AUTO_INCREMENT,
  `IngStockId` int(11) NOT NULL,
  `ProductoId` int(11) NOT NULL,
  `IngStockItemsCantidad` int(11) NOT NULL,
  `IngStockItemsPrecioUnitario` decimal(10,0) NOT NULL,
  `IngStockItemsPrecioTotal` decimal(10,0) NOT NULL,
  PRIMARY KEY (`IngStockItemsId`),
  KEY `IngStockId` (`IngStockId`),
  KEY `ProductoId` (`ProductoId`)
) ENGINE=InnoDB AUTO_INCREMENT=4229 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `MaeClientes` (
  `Vendedor` varchar(255) DEFAULT NULL,
  `Cod` int(10) DEFAULT NULL,
  `Nombre` varchar(255) DEFAULT NULL,
  `Domicilio` varchar(255) DEFAULT NULL,
  `EntreCalles` varchar(255) DEFAULT NULL,
  `Localidad` varchar(255) DEFAULT NULL,
  `CP` varchar(255) DEFAULT NULL,
  `Horario` varchar(255) DEFAULT NULL,
  `Contacto` varchar(255) DEFAULT NULL,
  `Teléfono fijo` varchar(255) DEFAULT NULL,
  `Celular` varchar(255) DEFAULT NULL,
  `Email` varchar(255) DEFAULT NULL,
  `RazonSocial` varchar(255) DEFAULT NULL,
  `TipoIVA` varchar(255) DEFAULT NULL,
  `cuit` varchar(255) DEFAULT NULL,
  `iva` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `marcas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `ofertas` (
  `id` int(11) NOT NULL,
  `titulo` varchar(255) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `fecha_inicio` date NOT NULL,
  `fecha_fin` date NOT NULL,
  `activa` tinyint(1) NOT NULL,
  `created_at` timestamp NOT NULL,
  `tipo` enum('unitaria','bundle','minima','mix') NOT NULL,
  `modo_precio` enum('precio_unitario','precio_pack','descuento_pct') NOT NULL,
  `valor_precio` decimal(12,2) DEFAULT NULL,
  `min_unidades_total` int(11) DEFAULT NULL,
  `unidad_base` enum('unidad','caja') DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `ofertas_backup` (
  `id` int(11) NOT NULL,
  `titulo` varchar(255) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `fecha_inicio` date NOT NULL,
  `fecha_fin` date NOT NULL,
  `activa` tinyint(1) NOT NULL,
  `created_at` timestamp NOT NULL,
  `tipo` enum('unitaria','bundle','minima','mix') NOT NULL,
  `modo_precio` enum('precio_unitario','precio_pack','descuento_pct') NOT NULL,
  `valor_precio` decimal(12,2) DEFAULT NULL,
  `min_unidades_total` int(11) DEFAULT NULL,
  `unidad_base` enum('unidad','caja') DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `ofertas_detalle` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `oferta_id` int(11) NOT NULL,
  `producto_id` int(11) NOT NULL,
  `unidades_fijas` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_oferta` (`oferta_id`),
  KEY `idx_producto` (`producto_id`),
  CONSTRAINT `fk_ofertas_detalle_oferta` FOREIGN KEY (`oferta_id`) REFERENCES `ofertas` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ofertas_detalle_producto` FOREIGN KEY (`producto_id`) REFERENCES `productos` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `origen` (
  `nombre` varchar(20) NOT NULL,
  PRIMARY KEY (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `pagos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `clienteId` int(11) NOT NULL,
  `tipoMedioPagoId` int(11) NOT NULL,
  `fechaRecep` date NOT NULL,
  `importe` decimal(16,2) NOT NULL,
  `receptor` varchar(255) NOT NULL,
  `observaciones` text DEFAULT NULL,
  `chFecha` date DEFAULT NULL,
  `chVto` date DEFAULT NULL,
  `chNumero` int(11) DEFAULT NULL,
  `chBanco` varchar(100) DEFAULT NULL,
  `estado` varchar(20) DEFAULT NULL,
  `procesado` char(1) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `clienteId` (`clienteId`),
  KEY `tipoMedioPagoId` (`tipoMedioPagoId`),
  KEY `receptor` (`receptor`),
  CONSTRAINT `pagos_ibfk_1` FOREIGN KEY (`clienteId`) REFERENCES `clientes` (`id`) ON DELETE NO ACTION,
  CONSTRAINT `pagos_ibfk_2` FOREIGN KEY (`tipoMedioPagoId`) REFERENCES `tipoMediosPago` (`id`) ON DELETE NO ACTION,
  CONSTRAINT `pagos_ibfk_3` FOREIGN KEY (`receptor`) REFERENCES `sec_users` (`login`) ON DELETE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=56071 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `parametros` (
  `Id` smallint(6) NOT NULL,
  `server` varchar(80) NOT NULL,
  `usr` varchar(80) NOT NULL,
  `pwd` varchar(80) NOT NULL,
  `port` varchar(80) NOT NULL,
  `conn_type` varchar(80) NOT NULL,
  `from_mail` varchar(80) NOT NULL,
  `attachment_url` varchar(255) NOT NULL,
  `app_entry_point` varchar(255) NOT NULL,
  `modo_trabajo` char(1) NOT NULL,
  `mail_alta_usuario` longtext NOT NULL,
  `helpMensajes` longtext DEFAULT NULL,
  `helpProveedores` longtext DEFAULT NULL,
  `capeta_store_docs` char(100) DEFAULT NULL,
  `enviaMails` char(1) DEFAULT NULL,
  `enviaWP` char(1) DEFAULT NULL,
  `matenimiento` char(1) DEFAULT NULL,
  `debug` char(1) DEFAULT NULL,
  `mails` char(1) DEFAULT NULL,
  `apiWP` char(50) DEFAULT NULL,
  `eviURL` varchar(100) DEFAULT NULL,
  `eviCuenta` varchar(100) DEFAULT NULL,
  `eviPwd` varchar(100) DEFAULT NULL,
  `eviMode` varchar(100) DEFAULT NULL,
  `eviPin` varchar(100) DEFAULT NULL,
  `eviPush` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`Id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `pedidoItems` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `pedidoId` int(11) NOT NULL,
  `productoId` int(11) NOT NULL,
  `cantidad` int(11) NOT NULL,
  `precioUnitario` decimal(16,2) NOT NULL,
  `precioTotal` decimal(16,2) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `productoId` (`productoId`),
  KEY `pedidoId` (`pedidoId`),
  CONSTRAINT `pedidoItems_ibfk_1` FOREIGN KEY (`productoId`) REFERENCES `productos` (`id`),
  CONSTRAINT `pedidoItems_ibfk_2` FOREIGN KEY (`pedidoId`) REFERENCES `pedidos` (`id`) ON DELETE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=60479 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `pedidos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `cliente` int(11) NOT NULL,
  `fecha` datetime NOT NULL,
  `login` varchar(255) NOT NULL,
  `estado` varchar(20) NOT NULL,
  `bultos` int(11) NOT NULL,
  `importeTotal` decimal(16,2) NOT NULL,
  `observacion` varchar(255) DEFAULT NULL,
  `fechaEntrega` date DEFAULT NULL,
  `saldo` decimal(16,2) DEFAULT NULL,
  `fechaSaldo` date DEFAULT NULL,
  `usuario` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `cliente` (`cliente`),
  KEY `login` (`login`),
  CONSTRAINT `pedidos_ibfk_1` FOREIGN KEY (`cliente`) REFERENCES `clientes` (`id`) ON DELETE NO ACTION,
  CONSTRAINT `pedidos_ibfk_2` FOREIGN KEY (`login`) REFERENCES `sec_users` (`login`)
) ENGINE=InnoDB AUTO_INCREMENT=26815 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `prepedidos_cabecera` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `cliente_id` int(11) NOT NULL,
  `fecha_creacion` datetime DEFAULT current_timestamp(),
  `estado` enum('borrador','enviado','terminado') DEFAULT 'borrador',
  `observaciones` text DEFAULT NULL,
  `importeTotal` decimal(12,2) NOT NULL DEFAULT 0.00 CHECK (`importeTotal` >= 0),
  PRIMARY KEY (`id`),
  KEY `idx_cliente_estado` (`cliente_id`,`estado`),
  KEY `idx_fecha_creacion` (`fecha_creacion`),
  CONSTRAINT `prepedidos_cabecera_ibfk_1` FOREIGN KEY (`cliente_id`) REFERENCES `clientes` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `prepedidos_items` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `prepedido_id` int(11) NOT NULL,
  `producto_id` int(11) NOT NULL,
  `ofertaid` int(11) DEFAULT NULL,
  `descripcion` varchar(255) NOT NULL,
  `cantidad` int(11) NOT NULL CHECK (`cantidad` > 0),
  `unidad` varchar(50) DEFAULT 'unidad',
  `precio_estimado` decimal(10,2) DEFAULT 0.00 CHECK (`precio_estimado` >= 0),
  `importe_unitario` decimal(12,2) NOT NULL DEFAULT 0.00 CHECK (`importe_unitario` >= 0),
  `observaciones` text DEFAULT NULL,
  `fecha_creacion` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_prepedido` (`prepedido_id`),
  KEY `idx_producto` (`producto_id`),
  KEY `idx_ofertaid` (`ofertaid`),
  CONSTRAINT `prepedidos_items_ibfk_1` FOREIGN KEY (`prepedido_id`) REFERENCES `prepedidos_cabecera` (`id`) ON DELETE CASCADE,
  CONSTRAINT `prepedidos_items_ibfk_2` FOREIGN KEY (`producto_id`) REFERENCES `productos` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=113 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `productos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `codigo` varchar(20) NOT NULL,
  `nombre` varchar(150) NOT NULL,
  `marca` int(11) DEFAULT NULL,
  `origen` varchar(20) NOT NULL,
  `pack` varchar(20) NOT NULL,
  `envase` int(11) DEFAULT NULL,
  `stockMinimo` int(11) DEFAULT NULL,
  `stockActual` int(11) DEFAULT NULL,
  `stockReservado` int(11) DEFAULT NULL,
  `precioCompra` decimal(10,2) DEFAULT NULL,
  `precioVenta` decimal(10,2) DEFAULT NULL,
  `rentabilidad` decimal(10,2) DEFAULT NULL,
  `foto` mediumblob DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `envase` (`envase`),
  KEY `marca` (`marca`),
  CONSTRAINT `productos_ibfk_1` FOREIGN KEY (`envase`) REFERENCES `envases` (`id`) ON DELETE NO ACTION,
  CONSTRAINT `productos_ibfk_3` FOREIGN KEY (`marca`) REFERENCES `marcas` (`id`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=451 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `ProdV2` (
  `Marca` varchar(255) DEFAULT NULL,
  `CODIGO` varchar(255) DEFAULT NULL,
  `DESCRIPCION` varchar(255) DEFAULT NULL,
  `ORIGEN` varchar(255) DEFAULT NULL,
  `PACK` varchar(255) DEFAULT NULL,
  `Litros` decimal(10,3) DEFAULT NULL,
  `categoria` varchar(255) DEFAULT NULL,
  `stock` int(10) DEFAULT NULL,
  `Stock minimo` int(10) DEFAULT NULL,
  `costo unitario` varchar(255) DEFAULT NULL,
  `Venta Unitario` int(10) DEFAULT NULL,
  `field_L` varchar(255) DEFAULT NULL,
  `field_M` varchar(255) DEFAULT NULL,
  `field_N` varchar(255) DEFAULT NULL,
  `field_O` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `proveedores` (
  `proveedorId` int(11) NOT NULL AUTO_INCREMENT,
  `proveedorNombre` char(100) NOT NULL,
  `proveedorTE` char(50) NOT NULL,
  `proveedorDireccion` char(100) NOT NULL,
  PRIMARY KEY (`proveedorId`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `sc_log` (
  `id` int(8) NOT NULL AUTO_INCREMENT,
  `inserted_date` datetime DEFAULT NULL,
  `username` varchar(90) NOT NULL,
  `application` varchar(200) NOT NULL,
  `creator` varchar(30) NOT NULL,
  `ip_user` varchar(32) NOT NULL,
  `action` varchar(30) NOT NULL,
  `description` text DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4123 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `sec_apps` (
  `app_name` varchar(128) NOT NULL,
  `app_type` varchar(255) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`app_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `sec_groups` (
  `group_id` int(11) NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`group_id`),
  UNIQUE KEY `description` (`description`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `sec_groups_apps` (
  `group_id` int(11) NOT NULL,
  `app_name` varchar(128) NOT NULL,
  `priv_access` varchar(1) DEFAULT NULL,
  `priv_insert` varchar(1) DEFAULT NULL,
  `priv_delete` varchar(1) DEFAULT NULL,
  `priv_update` varchar(1) DEFAULT NULL,
  `priv_export` varchar(1) DEFAULT NULL,
  `priv_print` varchar(1) DEFAULT NULL,
  PRIMARY KEY (`group_id`,`app_name`),
  KEY `sec_groups_apps_ibfk_2` (`app_name`),
  CONSTRAINT `sec_groups_apps_ibfk_1` FOREIGN KEY (`group_id`) REFERENCES `sec_groups` (`group_id`) ON DELETE CASCADE,
  CONSTRAINT `sec_groups_apps_ibfk_2` FOREIGN KEY (`app_name`) REFERENCES `sec_apps` (`app_name`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `sec_users` (
  `login` varchar(255) NOT NULL,
  `pswd` varchar(255) NOT NULL,
  `name` varchar(64) DEFAULT NULL,
  `email` varchar(255) DEFAULT NULL,
  `active` varchar(1) DEFAULT NULL,
  `activation_code` varchar(32) DEFAULT NULL,
  `priv_admin` varchar(1) DEFAULT NULL,
  PRIMARY KEY (`login`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `sec_users_groups` (
  `login` varchar(255) NOT NULL,
  `group_id` int(11) NOT NULL,
  PRIMARY KEY (`login`,`group_id`),
  KEY `sec_users_groups_ibfk_2` (`group_id`),
  CONSTRAINT `sec_users_groups_ibfk_1` FOREIGN KEY (`login`) REFERENCES `sec_users` (`login`) ON DELETE CASCADE,
  CONSTRAINT `sec_users_groups_ibfk_2` FOREIGN KEY (`group_id`) REFERENCES `sec_groups` (`group_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `tipoEnvase` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(150) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `tipoIva` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `tasa` decimal(10,2) NOT NULL,
  `discrimina` char(1) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `tipoMediosPago` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `datosAdic` char(1) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

CREATE TABLE IF NOT EXISTS `vendedores` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(150) NOT NULL,
  `login` varchar(255) NOT NULL,
  `TE` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `login` (`login`)
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;
