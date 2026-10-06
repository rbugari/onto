# Glosario comercial - Distribuidora (sintetico)

Cliente: Empresa con al menos un pedido facturado en el ERP. Se identifica por id_cliente.
Cliente activo: Cliente con al menos un pedido facturado en los ultimos 12 meses.
Cuenta: Registro del CRM que representa a un cliente o prospecto. Una cuenta puede no existir en el ERP.
Pedido: Solicitud de compra registrada en el ERP. Solo cuenta como venta cuando su estado es FACTURADO.
Venta neta: Importe facturado menos descuentos y notas de credito.
Margen bruto: Venta neta menos costo de mercaderia vendida.
Zona: Region comercial asignada al cliente. El presupuesto se define por zona y mes.
Oportunidad: Negocio potencial del CRM asociado a una cuenta.

## Reglas

- Un pedido ANULADO no debe incluirse en ventas ni en margen.
- El stock disponible debe tomarse del corte diario del lakehouse, excepto para reservas en linea.
- Una oportunidad ganada solo se considera venta si existe un pedido FACTURADO asociado.
