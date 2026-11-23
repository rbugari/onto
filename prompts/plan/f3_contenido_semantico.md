# F3 - Contenido semantico completo en el paquete

Lee `docs/18_PLAN_REPOSICIONAMIENTO.md` y las secciones 3, 4, 6 y 7 de `docs/15_INTEGRACION_FABRIC_DATABRICKS.md` (R1.1). Prerrequisito: F1 integrada. Rama: `plan/f3-contenido`.

## Objetivo
Que el paquete salga casi listo para cargar: menos `COMPLETAR`, mas contenido generado desde evidencia y marcado como propuesta hasta que una persona lo apruebe.

## Tareas (en `platform_exports.py`, `nexo.py`, `interoperability.py` y modelos relacionados)
1. Tipos de propiedad desde la metadata tecnica (mapear tipos SQL a `String`, `Boolean`, `DateTime`, `BigInt`, `Double` en Fabric; mantener `String` solo si no hay metadata).
2. Joins desde relaciones aprobadas y claves foraneas: join specs de Genie y `joins` de metric views.
3. Pages de Databricks completas: dominio, responsable, sinonimos, descripcion, cuerpo estructurado (Definicion, Uso de negocio, Ejemplos si hay evidencia) y activos relacionados y fuentes, con cita a la evidencia (archivo/fragmento). Un `.md` por concepto.
4. Descripciones de tablas y columnas (`COMMENT ON`) y sinonimos desde lo aprobado.
5. KPIs: si la expresion existe en la evidencia (documentacion o modelo BIM/TMDL), proponerla y marcarla `propuesta: requiere aprobacion`; si no existe, mantener `COMPLETAR_EXPRESION_AGREGADA`. Nunca inventar una expresion.
6. Ejemplos pregunta-SQL desde el catalogo de consultas y benchmarks desde la bateria de evaluacion existente, solo si ya estan aprobados.
7. Reporte de cobertura: agregar el conteo de campos `COMPLETAR` restantes por tipo, para medir el avance.

## Criterios de aceptacion
- En la demo comercial y la distribuida bajan los `COMPLETAR` y los tipos dejan de ser todos `String` donde hay metadata.
- Todo texto generado conserva la referencia a su evidencia.
- Ningun elemento no aprobado se presenta como aprobado.
- Tests nuevos: mapeo de tipos, join desde FK, Page con fuentes, KPI sin evidencia queda `COMPLETAR`.
- `.venv\Scripts\python.exe -m unittest discover -s tests` pasa.

## Fuera de alcance
Cambios de formato de plataforma (es F4), publicacion, LLM nuevo para generar texto: usar lo ya aprobado en Nexo.
