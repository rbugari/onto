# F4 - Formatos estables

Lee `docs/18_PLAN_REPOSICIONAMIENTO.md` y `docs/15_INTEGRACION_FABRIC_DATABRICKS.md`. Prerrequisito: F3 integrada. Rama: `plan/f4-formatos`.

## Objetivo
Que la entrega no dependa de un formato en preview que cambia: actualizar Fabric al modelo nuevo y sumar export a estandares abiertos.

## Antes de codificar (obligatorio)
Consultar la documentacion oficial actual y anotar en `docs/15_INTEGRACION_FABRIC_DATABRICKS.md` la version y fecha consultada:
- Microsoft Learn: Fabric IQ ontology (overview, how-to-import-export, definicion de item `Ontology` en la REST API).
- Apache Ossie: https://ossie.apache.org/ y su especificacion en GitHub (`apache/ossie`, `core-spec/spec.md`).
- Databricks: UC semantics, metric views YAML.
Si algo no se puede verificar, marcarlo experimental o `COMPLETAR`. No inventar campos.

## Tareas
1. Fabric modelo nuevo: adaptar el generador a la definicion actual (namespaces, entidades sin clave, metricas, reglas). Declarar en el paquete la version de formato y que la experiencia vieja se retira el 2027-01-31. Mantener aislado en `platform_exports.py` o dividir en un modulo por formato.
2. Export OWL/TTL: generar `ontology.ttl` desde la release (clases, propiedades, relaciones, etiquetas, descripciones, sinonimos como `skos:altLabel`). Incluir en el reporte de cobertura que elementos no se representan. Documentar que Fabric lo importa solo a una ontologia vacia.
3. Export Ossie YAML (experimental): modelo semantico con datasets, campos, metricas y relaciones desde lo aprobado. Etiquetarlo `experimental` y fijar la version de spec usada.
4. Databricks: revisar los formatos existentes contra la doc actual y corregir diferencias.
5. Agregar los nuevos archivos a la estructura del paquete, a la UI de Nexo (descarga ZIP) y a la seccion 4 del doc 15.
6. Plantilla de piloto: `docs/pilotos/PILOTO_VALIDACION_PLATAFORMAS.md` con pasos para cargar el paquete en un workspace real de Fabric y de Databricks y una tabla para registrar que acepto cada plataforma. No se ejecuta en esta fase.

## Criterios de aceptacion
- El TTL generado es valido (parsear con `rdflib` o validador equivalente; agregar la dependencia solo si es necesaria y registrarla en `requirements.txt`).
- El YAML de Ossie valida contra la spec consultada o queda explicitamente como experimental.
- Los tests existentes de interoperabilidad se actualizan al nuevo formato y pasan: `.venv\Scripts\python.exe -m unittest discover -s tests`.

## Fuera de alcance
Publicar en las plataformas, usar credenciales.
