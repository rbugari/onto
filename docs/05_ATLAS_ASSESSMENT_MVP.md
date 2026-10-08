# Atlas - Ontology Readiness Assessment

Estado: MVP operativo implementado
Producto: 1 de 3 de ONTO

## Que es Atlas

Atlas prepara la evidencia tecnica y funcional de un dominio. No pretende declarar una ontologia final: produce un baseline reproducible que permite saber con que evidencia se cuenta, que falta y que conviene priorizar antes de pasar a Nexo.

Evolucion acordada: medir la **cobertura explicativa** del alcance inventariado y compararla entre assessments. Las Partes 1 a 3 agregan el universo versionado y ajustable, la matriz reproducible y la accion explicita Evaluar cobertura con LLM en Diagnostico > Contraste semantico. Esta accion recorre todo el inventario incluido, compara evidencia documental y genera un assessment nuevo, con presupuesto, politica de datos, cache y fallos visibles sin fallback heuristico. El assessment normal sigue siendo determinista y sin evaluar. La verificacion tecnica usa proveedores simulados; falta contrastar calidad con un modelo real y una muestra humana. El score basal no es cobertura explicativa y explicado no significa aprobado. Entregables y pruebas por etapa: [Plan Atlas: cobertura explicativa](16_PLAN_ATLAS_COBERTURA_EXPLICATIVA.md).

Las Partes 4 y 5 completan el diagnostico operativo: cobertura por sistema/caso, filtros sin alterar denominadores, pedidos con responsable propuesto y criterio de cierre, y comparacion de dos assessments por identidad logica. Se separa completar un analisis de resolver una ausencia documental; cambios de alcance no generan un delta de avance. Los pedidos pueden mostrar Revisar cierre, pero no se cierran automaticamente ni aprueban conocimiento. La conexion real al LLM y la validacion semantica humana quedaron para el final por decision del usuario.

## Oferta de entrada: assessment de preparacion para agentes

Se vende un diagnostico acotado, apoyado por Atlas, no una implementacion de agentes ni una certificacion automatica. El resultado responde: que fuentes y definiciones existen, que se puede respaldar con evidencia, que falta documentar y cual es el siguiente trabajo necesario para habilitar casos de uso con IA.

### Alcance inicial propuesto

- Un dominio de negocio y uno o dos casos de uso acordados con el cliente.
- Fuentes tecnicas y documentos autorizados, con acceso de solo lectura donde aplique.
- Una persona responsable de negocio y una responsable de datos para validar hallazgos; la cantidad de entrevistas y activos se fija antes de presupuestar.
- No se incluyen cambios en sistemas fuente, publicacion externa, permisos productivos, desarrollo de agentes ni garantia de calidad de datos a nivel de filas.

### Pasos y recursos

| Paso | Trabajo | Responsable principal | Salida |
| --- | --- | --- | --- |
| 1. Encuadre | Elegir casos de uso, fuentes, restricciones de acceso y responsables. | Consultor y sponsor del cliente | Alcance y checklist de insumos. |
| 2. Recoleccion | Inventariar metadata, modelos y documentos; registrar origen y hashes. | Analista de datos con Atlas | Inventarios y evidencia. |
| 3. Contraste | Comparar estructura tecnica con terminos, KPIs y reglas; entrevistar referentes sobre ausencias y contradicciones. | Analista funcional y referentes del cliente | Hallazgos clasificados y pendientes de validacion. |
| 4. Diagnostico | Revisar score basal, priorizar gaps por impacto en los casos de uso y registrar decision humana. | Consultor y responsables del cliente | Assessment revisado y plan de regularizacion. |
| 5. Continuidad | Definir que documentacion se completa y en que plataforma se implementara despues. | Cliente con acompanamiento | Hoja de ruta y alcance de una segunda etapa. |

### Indice del dossier para el cliente

1. Resumen ejecutivo: alcance, estado observado y decisiones requeridas.
2. Casos de uso evaluados y preguntas que hoy se pueden o no respaldar.
3. Inventario de fuentes tecnicas y documentales, procedencia y limitaciones.
4. Evaluacion por dimension: puntaje, evidencia y nivel de confianza de los hallazgos.
5. Gaps priorizados: impacto, evidencia faltante, accion, responsable y criterio de cierre.
6. Plan de documentacion: glosario, KPIs, reglas, relaciones, ownership y permisos a completar.
7. Ruta de implementacion: Fabric, Databricks u otra opcion segun el entorno del cliente, con supuestos y trabajo pendiente.
8. Anexos trazables: inventarios, indice de evidencia, hashes y registro de revision.

El archivo `execution_summary.md` ya incluye lectura ejecutiva, casos de uso evaluados, sistemas en alcance, mapa entre sistemas, evidencia documental, dimensiones, gaps (con categoria, sistema y casos de uso afectados) y limites. **No cubre aun todo este indice**: confianza de hallazgos, responsables y criterio de cierre por gap, plan de documentacion y recomendacion de plataforma necesitan relevamiento y validacion humana. No se deben presentar como generados automaticamente.

### Orden de mejora del producto

1. Hecho: registrar casos de uso y sistemas, vincular gaps con sistema y caso de uso, y mapear entidades compartidas entre sistemas.
2. Validar el dossier con la demo distribuida y una persona ajena al desarrollo: debe entender que esta listo, que falta y por que.
3. Mejorar citas por pagina/seccion y distinguir ausencia, contradiccion y falta de aprobacion.
4. Agregar responsables y criterio de cierre por gap y plantillas Markdown para glosario, KPI y reglas, siempre con estado borrador/aprobado.
5. Llevar a Nexo la confirmacion de equivalencias entre sistemas.
6. Probar un destino real con el primer cliente que lo requiera. Para Fabric hoy hay lectura de metadata; Databricks se carga por archivo exportado. Ambos mappings son paquetes locales, no publicaciones.

**Definiciones a acordar con el primer cliente:** dominio y casos de uso, fuentes y permisos, referentes para revision, criterios de prioridad y plataforma destino. Sin esas decisiones, Atlas entrega un baseline, no un dictamen final de preparacion.

## Alcance implementado

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

- `manifest.json`: producto, version de formato, alcance, run, artefactos y resumen (score, gaps).
- `scope_definition.json`: cliente, dominio, responsable, casos de uso y sistemas en alcance.
- `semantic_inventory.json`: conceptos, objetos tecnicos detectados (con `source_id` del sistema de origen), relaciones y metadata disponible.
- `business_context_inventory.json`: resultado existente del scanner o declaracion explicita de ausencia.
- `source_inventory.json`: sistemas inventariados y declarados (plataforma, responsable, formato, hash SHA-256) y documentos cargados.
- `cross_source_map.json`: entidades presentes en mas de un sistema, clave comun detectada y entidades de un solo sistema.
- `evidence_index.json`: chunks, rangos y extractos que permiten ubicar la evidencia usada.
- `explanatory_scope.json`: universo explicativo versionado y decisiones de inclusion/exclusion.
- `explanatory_coverage.json`: estados, aspectos, citas verificadas y snapshots para reproducir el calculo.
- `explanatory_diagnosis.json`: contadores por sistema/caso y pedidos de informacion o analisis con responsable propuesto, prioridad y cierre.
- `readiness_score.json`: score basal determinista por dimension, en escala 0-5.
- `gap_backlog.json`: gaps con severidad, categoria, sistema y casos de uso afectados.
- `assessment_review.json`: checkpoint humano del baseline, sus gaps abiertos y la decision de revision; no aprueba una ontologia.
- `execution_summary.md`: resumen legible del run.

## Dominios distribuidos en varios sistemas

Un proyecto Atlas registra **todos los sistemas** que participan del dominio, aunque esten en plataformas distintas (ERP en MariaDB, lakehouse en Databricks, modelos Power BI, CRM en SQL Server, planillas). Cada sistema se inventaria por separado y reimportarlo reemplaza solo sus objetos.

| Plataforma | Como se carga |
| --- | --- |
| Databricks, SQL Server, PostgreSQL, Snowflake, Oracle | Archivo exportado: DDL (`.sql`) o `information_schema.columns` a CSV. |
| MariaDB / MySQL | `mysqldump --no-data` (`.sql`). |
| Power BI | `model.bim`, TMDL o PBIP `.zip`. |
| Microsoft Fabric | Conexion directa de solo lectura o export a CSV. |
| Planillas u otros | CSV con `table_name`, `column_name`, `data_type`. |

Con dos o mas sistemas, Atlas compara entidades por nombre normalizado (con un vocabulario bilingue minimo, por ejemplo `DimCustomer` = `clientes`) y busca una clave comun (`id_cliente`, `cliente_id`, `CustomerKey`). El resultado es orientativo: las equivalencias las confirman los responsables. La demo `scripts/run_distributed_demo.py` usa `docs/casos/ventas_distribuidas/`.

## Pantalla de Atlas

La pantalla (`onto_ui/atlas.py`) muestra el avance en cinco pasos y el siguiente paso sugerido, y se organiza en cuatro pestanas:

1. **Alcance:** cliente, dominio, producto de datos, responsable y casos de uso.
2. **Fuentes:** tabla de sistemas, alta de sistema, carga de metadata con ayuda segun la plataforma, conexion directa a Fabric, edicion o baja (con snapshot previo) y objetos inventariados.
3. **Contexto de negocio:** documentos, analisis y resultados por tipo (definiciones, KPIs, reglas, entidades vinculadas, preguntas para taller).
4. **Diagnostico:** generar, elegir un diagnostico, universo ajustable, cobertura y pedidos filtrables, comparacion con otro assessment, puntaje por dimension, brechas, mapa entre sistemas, sistemas evaluados, informe descargable y revision humana. La comparacion se descarga en JSON, sin modificar los paquetes originales.

Si el proyecto cambio despues del ultimo diagnostico, la pantalla lo marca como desactualizado.

## Que mide el score basal (perfil `atlas-baseline-v1`)

No es el scoring definitivo de readiness. Es una medida explicable para decidir el siguiente trabajo del piloto:

| Dimension | Evidencia inicial |
| --- | --- |
| `semantic_metadata` | tablas, columnas, medidas y relaciones disponibles. |
| `business_context` | documentos, definiciones, reglas y KPIs extraidos. |
| `semantic_business_linkage` | presencia de contexto y candidatos de cruce. |
| `governance_traceability` | estructura de proyecto, relaciones, fuentes disponibles y casos de uso declarados. |
| `cross_source_alignment` | solo con 2+ sistemas: cobertura de sistemas en alcance, entidades compartidas, clave comun y responsables. |

Si hay gaps de severidad alta, la lectura no puede ser `strong_foundation` aunque el promedio lo alcance.

Todos los valores se calculan sin LLM. El LLM puede generar contexto candidato antes del run, pero no decide el score basal.

El scanner admite una configuracion local `ONTO_LLM_*` o una referencia explicita `ONTO_LLM_CONFIG_PATH` a un proveedor compartido. Esta segunda opcion permite reutilizar un modelo para Atlas, Nexo y Argos sin copiar la clave al proyecto; solo se habilita para contenido que el usuario autorice enviar al proveedor.

## Limites actuales

- Los adaptadores técnicos disponibles son `model.bim`, TMDL, paquetes PBIP ZIP, payloads JSON de semantic model, DDL generico (`.sql`), exports de `information_schema.columns` (CSV), el descubrimiento de metadata Fabric de solo lectura y la ingesta de DDL MariaDB. Databricks y otras plataformas se cargan por archivo exportado; no hay descubrimiento remoto.
- El scanner fragmenta documentos, conserva `source_chunk_id` y el fragmento de evidencia, y los runners Risk y Ventas deduplican por contenido. Las citas por pagina/seccion dependen del parser de cada formato y quedan como evolucion posterior.
- Los gaps se basan en reglas iniciales y no reemplazan una revision funcional.
- Un modelo importado antes de la captura de evidencia puede usarse como inventario, pero Atlas lo marcara como gap hasta reimportar su archivo tecnico original.
- El paquete se guarda en carpetas locales y no publica en ninguna plataforma externa.

## Criterio de done de este corte

Un usuario puede elegir un proyecto, declarar alcance, casos de uso y sistemas, y obtener un assessment package local con un `run_id` unico. Cada sistema y documento incluido conserva hash, el score declara su perfil, el mapa entre sistemas y los gaps son inspeccionables sin ejecutar otro proceso.

El usuario tambien puede registrar la revision del baseline como `pending_review`, `reviewed` o `needs_follow_up`, con revisor, rol y nota. Esta decision queda en la carpeta `review/` del run y dentro del assessment package, pero no altera conceptos ni cambia el estado de una ontologia.
