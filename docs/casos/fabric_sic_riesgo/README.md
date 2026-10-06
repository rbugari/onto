# Caso: piloto Fabric, riesgo SIC

| | |
| --- | --- |
| Tipo | Real. Estructura del Warehouse y documentacion funcional; **sin datos de filas** |
| Objetivo | Dominio que vive en una sola plataforma (Fabric): Atlas sobre un Warehouse grande y consultas en vivo desde Argos |
| Ruta esperada | **A** en Fabric (la fuente ya esta en la plataforma) |
| Regenerar | Desde la UI (no tiene script) |

## Origenes

| Archivo | Que es |
| --- | --- |
| `input/fabric_warehouse_columns.csv` | Columnas del Warehouse `RAN_DE_DW_200_SILVER` en formato `information_schema.columns`, tomadas del descubrimiento en vivo del 2026-08-13. Esquemas `audit`, `bronze`, `silver`, `gold_sic`, `gold_lldt`, `gold_infra`, `gold_cultura`, `gold_governanca`, `queryinsights` |
| `input/documentation/GUIA_FUNCIONAL_CALCULO_GOLD_RIESGO.md` | Guia funcional del calculo Gold de riesgo |
| `input/documentation/CATALOGO_FUNCIONAL_REGLAS_RIESGO_VIGENTE.md` | Catalogo vigente de reglas (LLDT, SIC, CULTURA) |
| `input/documentation/CONTRATO_BI_GOLD_SIC_V2.md` | Contrato BI de la capa Gold SIC |

Limite: el descubrimiento original estaba acotado a 100 tablas y 2000 columnas. El CSV tiene esas 2000 columnas, que Atlas agrupa en 127 tablas; no trae claves foraneas.

## Dos formas de cargar la metadata

- **Offline (recomendada para pruebas repetibles)**: importar el CSV.
- **En vivo**: conexion de solo lectura a Fabric (configuracion Entra del proyecto). Atlas lee `INFORMATION_SCHEMA` con los mismos limites.

## Que cargar en Atlas (UI)

1. **Alcance**: cliente `fabric`, dominio `gold-sic-risk`, producto `risk`, con responsable. Casos de uso (los que cubre el catalogo de Argos):
   - Riesgo de una regla en un SIC (alta): "Cual es el riesgo de la regla 1 en el SIC 12?".
   - Distribucion de riesgos por nivel (media).
   - Estados REAL/DEFAULT de impactos (media).
2. **Fuentes**: sistema "Warehouse riesgo", plataforma Microsoft Fabric, con responsable; importar el CSV (o conectar en vivo).
3. **Contexto**: subir los 3 documentos **una vez** y analizar.
4. **Diagnostico**: generar.

## Resultado esperado

Con la carga offline completa (un caso de uso y responsables): **4,25 strong_foundation**.

| Dimension | Puntaje | Lectura |
| --- | --- | --- |
| Metadata tecnica | 4 | Cubierto (sin medidas ni relaciones declaradas) |
| Contexto de negocio | 5 | Cubierto |
| Cruce tecnico-negocio | 3 | Casi |
| Gobierno y trazabilidad | 5 | Cubierto |

Brecha restante: revision funcional de terminos (negocio).

## Despues de Atlas

- Argos usa el catalogo de riesgo (`risk_rule_sic`, `risk_sic`, `risk_levels`, `risk_summary`, `impact_statuses`, `impact_summary`) y requiere la conexion en vivo a Fabric.
- Entrega: paquete Fabric; las tablas son de la plataforma, por lo que la ruta esperada es A.
