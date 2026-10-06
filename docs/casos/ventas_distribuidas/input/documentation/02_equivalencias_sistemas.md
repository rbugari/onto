# Equivalencias entre sistemas (borrador del area de Datos)

Este documento resume lo que hoy se sabe sobre como se cruzan los sistemas. Esta incompleto.

| Concepto | ERP (MariaDB) | Lakehouse (Databricks) | Power BI | CRM |
| --- | --- | --- | --- | --- |
| Cliente | clientes.id_cliente | gold.dim_cliente.cliente_id | DimCustomer.CustomerKey | Accounts.ErpCustomerCode (parcial) |
| Producto | productos.id_producto | gold.dim_producto.producto_id | DimProduct.ProductKey | no aplica |
| Venta | pedidos + pedido_items (estado FACTURADO) | gold.fact_ventas | FactSales | Opportunities (solo pipeline) |

Pendientes:

- Como se vincula una cuenta del CRM sin ErpCustomerCode con un cliente del ERP?
- fact_ventas tiene venta_id pero FactSales no tiene clave propia: se puede conciliar linea a linea?
- Quien es responsable del CRM y de las planillas de presupuesto?
