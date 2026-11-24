# Plan de reposicionamiento (2026-11)

Estado: aprobado para ejecutar fase a fase. Cada fase tiene un prompt autonomo en [prompts/plan/](../prompts/plan/).

## Posicionamiento

> ONTO prepara el conocimiento de negocio que las plataformas necesitan y no pueden generar solas: llega a Silver, cruza varios sistemas y lo entrega aprobado, listo para cargar.

- Las ontologias y capas semanticas de Fabric IQ y Databricks parten de la capa Gold y de su propio ecosistema.
- Alguien tiene que escribir y aprobar el contenido (Pages, descripciones, sinonimos, reglas, instrucciones de agente). ONTO lo prepara con evidencia.
- ONTO no compite: no es runtime, ni catalogo, ni reemplazo de la ontologia de la plataforma.

## Objetivos

| # | Objetivo | Medida |
| --- | --- | --- |
| O1 | Cubrir Silver, Bronze y sistemas fuera de la plataforma | Un dominio en 3 o mas sistemas llega a una release aprobada |
| O2 | Producir el contenido semantico a partir de evidencia | Pages, descripciones, sinonimos y reglas generados, con trazabilidad |
| O3 | Entregar en formatos que no se rompan | Export validado en la plataforma y en estandar abierto (OWL/TTL) |
| O4 | Producto chico y enfocado | Argos como banco de prueba; sin conectores nuevos |

## Fases

| Fase | Contenido | Esfuerzo | Depende de |
| --- | --- | --- | --- |
| F1 | Foco y limpieza: posicionamiento y congelado de alcance | 1-2 sem | - |
| F2 | Atlas: capa (Bronze/Silver/Gold) y viabilidad por plataforma | 3-4 sem | F1 |
| F3 | Contenido semantico completo en el paquete (R1.1) | 3-4 sem | F1 |
| F4 | Formatos estables: Fabric modelo nuevo, OWL/TTL, Ossie experimental | 2-3 sem | F3 |
| F5 | Importar lo que la plataforma ya tiene como evidencia (opcional) | 2-3 sem | F2, F4 |

F4 es urgente por fecha: la experiencia vieja de Ontology en Fabric se retira el 31/01/2027. F2 y F3 son el diferencial.

### Estado (2026-11-24)

| Fase | Estado |
| --- | --- |
| F1 Foco y limpieza | Hecha |
| F2 Capa y viabilidad en Atlas | Hecha |
| F3 Contenido semantico en el paquete | Hecha (sin ejemplos SQL ni benchmarks: la release no guarda SQL aprobado) |
| F4 Formatos estables | Hecha en codigo y tests; **falta validar en workspaces reales** ([plantilla de piloto](pilotos/PILOTO_VALIDACION_PLATAFORMAS.md)). Hallazgo: la ontologia nueva de Fabric es TMDL, no el JSON anterior |
| F5 Importar lo existente | Opcional; decidir despues del piloto |

## No hacer

- Conectores de publicacion directa (release 2 del [doc 15](15_INTEGRACION_FABRIC_DATABRICKS.md)).
- Nuevas capacidades en Argos ni nuevos adapters.
- Sincronizacion bidireccional.
- Competir cuando todo vive en una sola plataforma y esta en Gold.

## Contexto de mercado (verificado 2026-11-23, documentacion oficial)

- Fabric IQ Ontology: preview. Genera desde semantic models, agente de ontologia con propuesta y revision, import/export RDF/TTL/OWL (solo en ontologia vacia), versiones. Semantic views: preview (YAML basado en Apache Ossie).
- Databricks: metric views, dominios y Pages (documentadas sin etiqueta Beta); Wikis y relaciones entre metric views en Beta; Genie Ontology combina conocimiento modelado y aprendido; fuentes externas (Power BI) en Beta; servidor MCP.
- Apache Ossie (ex OSI): estandar abierto en incubacion, version 0.3 dev.
- Confirmar el estado GA de Pages y Genie Ontology antes de afirmarlo a un cliente.

## Hallazgos F1

- **Cobertura explicativa (`explanatory_coverage.py`, `explanatory_analysis.py`, `explanatory_scope.py`, [doc 16](16_PLAN_ATLAS_COBERTURA_EXPLICATIVA.md)): mantener.** Contesta cuanto del alcance se puede explicar con evidencia y que falta, algo que el scanner de contexto no mide (solo extrae). Es la base de "que queda sin significado" que F2 necesita; no se solapa con las plataformas.
- **Congelado:** Argos como runtime de plan B y sus adapters, y los conectores R2/R3 (ver [MVP operativo](00_MVP_OPERATIVO.md)). Argos sigue como banco de prueba.
- **UI:** solo cambio el subtitulo de Argos (sin menciones a plan B). Navegacion y pantallas intactas.
- **Entorno:** el repo se valida con `unittest` (no hay pytest instalado).

## Reglas para el agente autonomo (aplican a todas las fases)

- Una fase por ejecucion. No empezar la siguiente.
- Trabajar en una rama `plan/fN-<tema>`; no tocar `main`; no hacer push.
- Cambios minimos y dirigidos; no refactorizar fuera del alcance de la fase.
- No borrar codigo de Argos ni de conectores: solo marcar como congelado.
- Idioma de documentos: espanol sin tildes dobles de formato, como el resto de `docs/`.
- Validar con `.venv\Scripts\python.exe -m unittest discover -s tests` antes de dar por cerrada la fase; los tests existentes no deben romperse.
- Agregar tests solo para comportamiento nuevo.
- Al terminar: commit con mensaje claro, y un resumen con lo hecho, lo que quedo pendiente y las decisiones que requieren al usuario.
- Si falta una decision de producto, parar y preguntar en vez de inventar.
- Nunca inventar datos de plataforma: si no se puede verificar un formato, marcarlo como `COMPLETAR` o experimental.
