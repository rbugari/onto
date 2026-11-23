# F5 - Importar lo que la plataforma ya tiene como evidencia (opcional)

Decidir si se ejecuta despues del piloto de F4. Lee `docs/18_PLAN_REPOSICIONAMIENTO.md`. Prerrequisito: F2 y F4 integradas. Rama: `plan/f5-importar`.

## Objetivo
Que Atlas reconozca el conocimiento que Fabric o Databricks ya tienen (semantic models, metric views, Pages, ontologias exportadas) y lo cruce con los sistemas que esas plataformas no ven, marcando contradicciones.

## Tareas
1. Importadores por archivo (sin conexion en vivo), reutilizando `semantic_model_importer.py`, `bim_importer.py` y `external_metadata.py`:
   - metric view YAML de Databricks (medidas, dimensiones, joins, sinonimos);
   - Pages en Markdown (concepto, sinonimos, dominio);
   - ontologia exportada en TTL/OWL (clases, propiedades, relaciones).
2. Registrar lo importado como evidencia de tipo `plataforma_existente`, con sistema, archivo, hash y fragmento.
3. Cruce: en Atlas, detectar (a) conceptos que ya existen en la plataforma y en otros sistemas con nombres distintos, (b) conceptos del dominio sin cobertura en la plataforma, (c) definiciones que se contradicen entre fuentes. Nuevas brechas en el diagnostico.
4. Nexo: los candidatos que ya existen en la plataforma se muestran como "ya implementado", para no volver a entregarlos.
5. Documentar en `docs/05_ATLAS_ASSESSMENT_MVP.md` y `docs/15_INTEGRACION_FABRIC_DATABRICKS.md` (reemplaza el antiguo R3).

## Criterios de aceptacion
- Una demo con una metric view y un TTL de ejemplo muestra las tres clases de hallazgo.
- Tests nuevos para cada importador y para la deteccion de contradicciones.
- `.venv\Scripts\python.exe -m unittest discover -s tests` pasa.

## Fuera de alcance
Lectura remota, escritura en plataformas, sincronizacion.
