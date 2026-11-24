# Piloto: validar los paquetes en plataformas reales

Objetivo: comprobar que lo que genera ONTO se carga en Fabric y en Databricks, y registrar que acepto cada plataforma. Requiere workspaces habilitados; no lo ejecuta ONTO.

Prerrequisitos
- Una release aprobada (por ejemplo, la demo distribuida: `python scripts/run_distributed_demo.py`) y su paquete generado desde Nexo.
- Fabric: workspace con capacidad Fabric, Fabric IQ habilitado y permiso para crear items Ontology. Tenant: "Users can create ontology (preview) items".
- Databricks: workspace con Unity Catalog, un SQL warehouse, Genie y permiso de creacion de Pages en el dominio.

## Fabric

1. Crear la ontologia desde `fabric/ontology/create_ontology_request.json` (API) o sincronizando la carpeta `<Nombre>.Ontology` por Git.
2. Alternativa: crear una ontologia vacia e importar `open_standards/ontology.ttl`; guardar el resumen de importacion (preservado, ajustado, no soportado).
3. Agregar los data bindings en el editor y crear el Data Agent con las instrucciones del paquete.
4. Hacer 3 preguntas de la release y una fuera de alcance.

## Databricks

1. Ejecutar `unity_catalog_comments.sql`.
2. Cargar las Pages de `pages/` y crear una metric view de `metric_views/` completando la expresion.
3. Crear el Genie Agent con `genie_agent_create_request.json`.
4. Hacer 3 preguntas de la release y una fuera de alcance.

## Registro de resultados

| Plataforma | Paso | Resultado (acepto / acepto con ajustes / rechazo) | Mensaje o ajuste necesario | Fecha | Responsable |
| --- | --- | --- | --- | --- | --- |
| Fabric | Crear ontologia (API o Git) | | | | |
| Fabric | Importar `ontology.ttl` | | | | |
| Fabric | Data Agent con instrucciones | | | | |
| Databricks | `unity_catalog_comments.sql` | | | | |
| Databricks | Pages (bulk import) | | | | |
| Databricks | Metric view | | | | |
| Databricks | Genie Agent (`serialized_space`) | | | | |

Con los resultados, ajustar `fabric_ontology.py`, `platform_exports.py` u `open_standards.py` y anotar en el [doc 15](../15_INTEGRACION_FABRIC_DATABRICKS.md) la version de formato probada.
