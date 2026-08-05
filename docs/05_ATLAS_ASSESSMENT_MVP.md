# Atlas - Ontology Readiness Assessment

Estado: primer corte vertical implementado  
Producto: 1 de 3 de ONTO

## Que es Atlas

Atlas cartografia la base tecnica y funcional disponible para un dominio. No pretende declarar una ontologia final: produce un baseline reproducible que permite saber con que evidencia se cuenta, que falta y que conviene priorizar antes de pasar a Registry & Validation.

## Primer corte implementado

Desde un proyecto local existente, Atlas genera una ejecucion bajo:

```text
data/workspaces/<client>/<domain>/<data-product>/runs/<run-id>/
  input/
  working/
  evidence/
  review/
  publication/
  output/assessment-package/
```

El paquete de salida contiene:

- `manifest.json`: producto, version de formato, alcance, run y artefactos.
- `semantic_inventory.json`: conceptos, objetos BIM detectados, relaciones y metadata disponible.
- `business_context_inventory.json`: resultado existente del scanner o declaracion explicita de ausencia.
- `source_inventory.json`: documentos cargados y artefacto tecnico importado, con estado, hash SHA-256 y referencia local.
- `evidence_index.json`: chunks, rangos y extractos que permiten ubicar la evidencia usada.
- `readiness_score.json`: score basal determinista por dimension, en escala 0-5.
- `gap_backlog.json`: gaps iniciales con severidad y recomendacion.
- `assessment_review.json`: checkpoint humano del baseline, sus gaps abiertos y la decision de revision; no aprueba una ontologia.
- `execution_summary.md`: resumen legible del run.

## Que mide el score basal v0

No es el scoring definitivo de readiness. Es una medida explicable para decidir el siguiente trabajo del piloto:

| Dimension | Evidencia inicial |
| --- | --- |
| `semantic_metadata` | tablas, columnas, medidas y relaciones disponibles. |
| `business_context` | documentos, definiciones, reglas y KPIs extraidos. |
| `semantic_business_linkage` | presencia de contexto y candidatos de cruce. |
| `governance_traceability` | estructura de proyecto, relaciones y fuentes disponibles. |

Todos los valores se calculan sin LLM. El LLM puede generar contexto candidato antes del run, pero no decide el score basal.

El scanner admite una configuracion local `ONTO_LLM_*` o una referencia explicita `ONTO_LLM_CONFIG_PATH` a un proveedor compartido. Esta segunda opcion permite reutilizar un modelo para Atlas, Nexo y el futuro Runtime sin copiar la clave al proyecto; solo se habilita para contenido que el usuario autorice enviar al proveedor.

## Limites actuales

- El adaptador tecnico disponible es `model.bim`: al importarlo, ONTO guarda una copia local y su hash como evidencia. PBIP, TMDL, API Fabric y Databricks vienen despues.
- El scanner ya fragmenta documentos y conserva `source_chunk_id` y fragmento de evidencia. Las citas por pagina/seccion dependen del parser de cada formato y se incorporaran despues.
- Los gaps se basan en reglas iniciales y no reemplazan una revision funcional.
- Un modelo importado antes de la captura de evidencia puede usarse como inventario, pero Atlas lo marcara como gap hasta reimportar su archivo tecnico original.
- El paquete se guarda en carpetas locales y no publica en ninguna plataforma externa.

## Criterio de done de este corte

Un usuario puede elegir un proyecto, declarar cliente/dominio/data product y obtener un assessment package local con un `run_id` unico. Cada documento incluido conserva hash, el score declara su perfil y los gaps son inspeccionables sin ejecutar otro proceso.

El usuario tambien puede registrar la revision del baseline como `pending_review`, `reviewed` o `needs_follow_up`, con revisor, rol y nota. Esta decision queda en la carpeta `review/` del run y dentro del assessment package, pero no altera conceptos ni cambia el estado de una ontologia.
