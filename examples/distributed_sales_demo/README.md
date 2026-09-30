# Distributed Sales Demo

Demo sintetica de Atlas para un dominio comercial repartido en varios sistemas y plataformas.

| Sistema | Plataforma | Archivo en `input/` |
| --- | --- | --- |
| ERP operativo | MariaDB | `erp_mariadb.sql` |
| Lakehouse analitico | Databricks | `lakehouse_databricks_columns.csv` |
| Modelo Power BI Ventas | Power BI | `powerbi_ventas.bim` |
| CRM comercial | SQL Server | `crm_sqlserver.sql` |
| Planillas de presupuesto | Planillas | sin metadata (declarado) |

`input/scope.json` declara sistemas, responsables y tres casos de uso. `input/documentation/` tiene glosario, equivalencias entre sistemas y KPIs.

El caso demuestra:

- inventario de varios sistemas en un mismo proyecto;
- mapa de entidades compartidas (Cliente, Producto, Venta) y claves comunes;
- gaps por sistema sin responsable, sistema sin metadata y entidad sin clave comun;
- priorizacion de gaps por caso de uso.

No contiene datos reales. Se ejecuta con:

```powershell
python scripts/run_distributed_demo.py
```
