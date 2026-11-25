# Nalub: contexto funcional para un primer relevamiento

## Para que se usa

Nalub es una aplicacion interna de gestion comercial para una PYME que vende productos con distintas presentaciones o envases. Se usa para gestionar pedidos de clientes, controlar existencias, registrar mercaderia recibida de proveedores y administrar cobros y deudas. Trabajan vendedores y personal administrativo.

Esta descripcion resume el relevamiento funcional del 2026-08-12. El esquema SQL que la acompana fue extraido de un backup del 2026-04-02. No se verifico aqui el codigo actual ni una base en vivo; pueden existir diferencias entre ambas fechas. El SQL permite conocer la estructura de ese backup, pero por si solo no demuestra como funciona hoy cada proceso.

## Como se trabaja con los pedidos

Un vendedor selecciona un cliente y carga productos, cantidades y precios. El pedido tiene una cabecera y renglones de detalle. Al guardarlo inicialmente queda en Borrador, sin reservar existencias. Segun el relevamiento, el importe de cada renglon resulta de cantidad por precio unitario, y el importe del pedido suma sus renglones.

Confirmar un borrador lo pasa al estado Pedido y reserva las cantidades solicitadas si hay disponibilidad suficiente. Procesarlo lo pasa a Procesado: descuenta las cantidades del stock fisico y libera la reserva correspondiente. La entrega se registra despues, con fecha y usuario, y pasa el pedido a Entregado. Segun la documentacion, en ese momento aumenta la deuda del cliente, no al crear ni al confirmar el pedido.

Es posible cancelar un Borrador o un Pedido confirmado. Si tenia una reserva, se libera. Los pedidos procesados o entregados no se cancelan ni editan por ese mecanismo. El relevamiento diferencia capacidades del servicio de controles de pantalla todavia parcialmente conectados; no debe suponerse que toda funcion prevista esta operativa.

## Productos y existencias

Los productos tienen codigo, descripcion, presentacion o envase y precios de compra y venta. Se distingue el stock fisico del stock reservado. La disponibilidad se describe como stock actual menos stock reservado; no como una existencia adicional independiente.

Los ingresos de mercaderia registran proveedor, comprobante, fecha y renglones con productos, cantidades y precios de compra. Aumentan las existencias y actualizan el precio de compra segun el relevamiento. Un producto con historial no deberia eliminarse como si nunca hubiera tenido movimientos.

## Cobros y deuda

Se registran cobros de clientes, su fecha, importe y medio de pago. Un cobro puede distribuirse entre varios pedidos pendientes. La documentacion describe una aplicacion por antiguedad, sin permitir cobrar mas que la deuda pendiente.

El sistema conserva una deuda acumulada del cliente y tambien saldos por pedido. No son el mismo dato. El relevamiento indica que la entrega aumenta la deuda del cliente y que los cobros reducen saldos de pedidos y actualizan la deuda agregada. La conciliacion entre ambos niveles requiere confirmacion; no se garantiza que coincidan en todos los registros legacy.

## Ofertas y limites del relevamiento

Hay gestion de ofertas para productos con vigencia por fechas y habilitacion manual. En el relevamiento, su gestion es independiente y su aplicacion al crear o confirmar pedidos no esta integrada de punta a punta. No corresponde asumir que todos los renglones de un pedido tengan una oferta asociada.

Hay nombres diferentes entre modulos y referencias a pedidos y prepedidos. No esta confirmado que representen el mismo proceso ni que puedan unificarse. Las tablas de respaldo, auxiliares o legacy tampoco demuestran por su nombre que sigan en uso.

La auditoria es parcial. No se dispone de un historial completo de cada transicion o edicion. Facturacion, reportes avanzados y administracion completa de clientes no se describen como capacidades operativas actuales.