# Caso: ventas en un dominio distribuido (cinco sistemas)

| | |
| --- | --- |
| Tipo | Sintetico (sin datos reales) |
| Objetivo | Probar el inventario multi-sistema, el mapa de entidades compartidas y la ruta mixta |
| Ruta esperada | **B** en Fabric (26/39) y en Databricks (33/45): ERP y CRM no son alcanzables sin puente |
| Regenerar | `python scripts/run_distributed_demo.py` (agregar `--keep` para no borrar lo anterior) |

## Origenes

| Sistema | Plataforma | Archivo en `input/` | Responsable |
| --- | --- | --- | --- |
| ERP operativo | MariaDB | `erp_mariadb.sql` | Jefe de Sistemas |
| Lakehouse analitico | Databricks | `lakehouse_databricks_columns.csv` | Lider de Datos |
| Modelo Power BI Ventas | Power BI | `powerbi_ventas.bim` | Analista BI |
| CRM comercial | SQL Server | `crm_sqlserver.sql` | **sin responsable** (a proposito) |
| Planillas de presupuesto | Planillas | **sin archivo** (a proposito) | Control de Gestion |

`input/scope.json` declara los sistemas y tres casos de uso. `input/documentation/` tiene glosario, equivalencias entre sistemas y KPIs.

## Que cargar en Atlas (UI)

1. **Alcance**: cliente `demo-distribuidora`, dominio `comercial`, producto `ventas-distribuidas`, responsable Gerencia Comercial. Casos de uso de `scope.json`:
   - Rentabilidad por cliente (alta): ERP, lakehouse, Power BI.
   - Pipeline vs ventas reales (media): CRM, ERP.
   - Cumplimiento de presupuesto (alta): lakehouse, planillas.
2. **Fuentes**: registrar los cinco sistemas con la plataforma y responsable de la tabla; importar el archivo de cada uno (las planillas quedan declaradas sin archivo).
3. **Contexto**: subir los 3 documentos y analizar.
4. **Diagnostico**: generar.

## Resultado esperado

**4,0 partial_foundation** (la brecha alta impide `strong`).

| Dimension | Puntaje | Lectura |
| --- | --- | --- |
| Metadata tecnica | 5 | Cubierto |
| Contexto de negocio | 5 | Cubierto |
| Cruce tecnico-negocio | 3 | Casi |
| Gobierno y trazabilidad | 5 | Cubierto |
| Alineacion entre sistemas | 2 | Falta |

Entidades compartidas: Cliente y Producto (ERP, lakehouse, Power BI) con clave comun; Venta (lakehouse, Power BI) **sin** clave comun.

Brechas (todas intencionales):

- alta / fuentes: planillas de presupuesto sin metadata;
- media / gobierno: CRM sin responsable;
- media / entre_sistemas: Venta sin clave comun;
- media / negocio: revision funcional pendiente.

## Despues de Atlas

El script aprueba todo (solo para la demo), emite la release y genera los paquetes para Fabric y Databricks con ruta B.
