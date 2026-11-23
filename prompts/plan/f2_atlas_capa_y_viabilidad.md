# F2 - Atlas: capa de datos y viabilidad por plataforma

Lee `docs/18_PLAN_REPOSICIONAMIENTO.md`, `docs/05_ATLAS_ASSESSMENT_MVP.md` y las secciones 4 y 7 de `docs/15_INTEGRACION_FABRIC_DATABRICKS.md`. Prerrequisito: F1 integrada. Rama: `plan/f2-atlas`.

## Objetivo
Que Atlas diga que parte del dominio entiende ya la plataforma (Gold) y que queda sin significado (Silver, Bronze, sistemas externos), y si cada fuente es alcanzable por Fabric o Databricks.

## Tareas
1. Capa por activo: agregar a la metadata tecnica un atributo `layer` (`bronze`, `silver`, `gold`, `unknown`). Inferirlo de forma determinista: primero un valor declarado por el usuario al registrar el sistema o activo, luego convenciones de nombre/esquema (`bronze|raw`, `silver|clean|stg`, `gold|mart|dim_|fact_`). Siempre exponer `layer_source` (`declared` o `inferred`). Archivos probables: `atlas.py`, `models.py`, `external_metadata.py`, `context_scanner.py`.
2. Cobertura por capa: en el assessment, para cada entidad compartida o candidata, indicar en que capas existe y si tiene definicion documentada. Nueva brecha: "entidad solo documentada en Gold" y "entidad sin definicion en ninguna capa".
3. Viabilidad por plataforma (R1.2 del doc 15): por cada sistema, estimar `reachable_by` para Fabric y Databricks y el puente sugerido (mirroring, shortcut, copy job, Lakehouse Federation, ingesta). Reutilizar la logica de ruta A/B/C de `platform_exports.py`, extrayendola a un modulo compartido en vez de duplicarla.
4. Informe: agregar una seccion "Que entiende hoy la plataforma y que queda sin significado" al informe descargable y a la UI de Atlas (`onto_ui/atlas.py`), breve.
5. Documentar en `docs/05_ATLAS_ASSESSMENT_MVP.md`. Aclarar que capa y viabilidad son heuristicas que confirma una persona.

## Criterios de aceptacion
- Con la demo distribuida (`scripts/run_distributed_demo.py`) el informe muestra capas y viabilidad por plataforma y coincide con las rutas del doc 15 (B en ambas).
- Con el caso Nalub la viabilidad da ruta C para ambas.
- Tests nuevos: inferencia de capa (declarada gana a inferida), brecha "solo Gold", viabilidad por fuente.
- `.venv\Scripts\python.exe -m unittest discover -s tests` pasa.

## Fuera de alcance
Conexiones remotas, descubrimiento en vivo, cambios en Nexo.
