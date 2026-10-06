# Casos de prueba

Cada carpeta contiene **los origenes** de un caso: todo lo necesario para regenerarlo desde cero, una y otra vez, sin depender de `data/`.

```text
docs/casos/<caso>/
  README.md        que demuestra, que cargar en cada pestana de Atlas, resultado esperado y como regenerar
  input/           archivos tecnicos (DDL, CSV, model.bim) y alcance
  input/documentation/   documentacion funcional
```

| Caso | Tipo | Fuentes | Ruta esperada | Regenerar |
| --- | --- | --- | --- | --- |
| [comercial_powerbi](comercial_powerbi/README.md) | Sintetico, una fuente | Power BI (`model.bim`) | A en Fabric | `python scripts/run_commercial_sales_demo.py` |
| [ventas_distribuidas](ventas_distribuidas/README.md) | Sintetico, cinco sistemas | MariaDB, Databricks, Power BI, SQL Server, planillas | B en Fabric y Databricks | `python scripts/run_distributed_demo.py` |
| [nalub_mariadb](nalub_mariadb/README.md) | Real, una fuente legacy | MariaDB (solo esquema) | C (ONTO como plan B) | `python scripts/run_nalub_case.py` |
| [fabric_sic_riesgo](fabric_sic_riesgo/README.md) | Real, piloto Fabric | Warehouse Fabric (CSV offline o conexion en vivo) | A en Fabric | Desde la UI (ver README del caso) |

## Como leer el resultado de Atlas

El diagnostico puntua de 0 a 5 cada dimension y lista brechas por categoria (`fuentes`, `entre_sistemas`, `alcance`, `gobierno`, `negocio`).

| Lectura | Puntaje | Significado |
| --- | --- | --- |
| Cubierto | 4-5 | La dimension tiene lo necesario para pasar a Nexo. |
| Casi | 3 | Hay base, pero falta completar (revision funcional, claves, responsables). |
| Falta | 0-2 | Hay que conseguir informacion antes de seguir. |

La lectura general es `strong_foundation` (>= 4), `partial_foundation` (>= 2,5) o `early_foundation`. Una brecha de severidad alta impide `strong_foundation`.

## Reglas

- Los scripts borran y regeneran **solo** los artefactos de su caso en `data/`. Los perfiles de conexion (`data/connections/`) nunca se borran.
- Desde la UI, cargar cada documento **una sola vez**: subirlo de nuevo crea un duplicado.
- No guardar aca datos de filas ni credenciales: solo estructura (DDL/CSV/modelo) y documentacion. Ver [politica de datos](../09_DEMO_DATA_POLICY.md).
