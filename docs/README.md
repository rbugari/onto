# Documentacion de producto

Esta carpeta es la fuente de verdad del producto ONTO. Define una **Ontology Factory** formada por tres productos independientes y conectables, y distingue entre el plano de datos y el plano ontologico.

## Por donde empezar

1. [Objetivo, alcance y foco](OBJETIVO_ALCANCE_Y_FOCO.md): para que existe ONTO, que problema resuelve (dominios con datos distribuidos en varios sistemas), que incluye hoy y que no.
2. [Guia paso a paso no tecnica](GUIA_PASO_A_PASO_NO_TECNICA.md): ONTO explicado para negocio y gerencia, con el recorrido completo en lenguaje simple.
3. [MVP operativo de ONTO](00_MVP_OPERATIVO.md): como trabajar con la release local actual, proyectos validados y limites.

| Documento | Proposito |
| --- | --- |
| [Objetivo, alcance y foco](OBJETIVO_ALCANCE_Y_FOCO.md) | Documento de entrada: objetivo, problema, foco, alcance y metricas de exito. |
| [Guia paso a paso no tecnica](GUIA_PASO_A_PASO_NO_TECNICA.md) | Explicacion sin tecnicismos para comunicar ONTO a personas de negocio. |
| [MVP operativo](00_MVP_OPERATIVO.md) | Fuente de verdad para trabajar con la release local actual. |
| [Diagnostico y transformacion](01_DIAGNOSTICO_Y_TRANSFORMACION.md) | Explica el estado real del MVP, las brechas y que se conserva o transforma. |
| [PRD de Ontology Factory](02_PRD_ONTOLOGY_FACTORY.md) | Define problema, usuarios, productos, contratos, alcance y criterios de exito. |
| [Plan de alto nivel](03_PLAN_ALTO_NIVEL.md) | Ordena las fases, entregables, dependencias y gates de decision. |
| [Decision de arquitectura MVP](04_DECISION_ARQUITECTURA_MVP.md) | Fija el monolito web local como limite intencional de esta etapa. |
| [Atlas - Assessment MVP](05_ATLAS_ASSESSMENT_MVP.md) | Contrato y alcance del Producto 1 en el MVP operativo. |
| [Nexo - Registry & Validation MVP](06_NEXO_REGISTRY_MVP.md) | Contrato y alcance del Producto 2 en el MVP operativo. |
| [Argos - Runtime & Evaluation MVP](07_ARGOS_RUNTIME_MVP.md) | Contrato, límites y batería de evaluación del Producto 3. |
| [Interoperabilidad MVP](08_INTEROPERABILIDAD_MVP.md) | Planos de datos y ontologico; paquetes locales para Fabric y Databricks. |
| [Politica de datos demo](09_DEMO_DATA_POLICY.md) | Reglas para ejemplos, pilotos y artefactos locales. |
| [Posicionamiento y limites](10_POSITIONING_AND_BOUNDARIES.md) | Mensaje publico, productos, limites y anti-promesas. |
| [Estrategia de exportacion e interoperabilidad](11_EXPORT_AND_INTEROPERABILITY_STRATEGY.md) | Separacion entre fuentes de datos, modelos ontologicos y destinos. |
| [Demo end-to-end](12_DEMO_END_TO_END.md) | Guiones reproducibles: dominio distribuido (Atlas) y demo comercial completa. |
| [Fuente de verdad para presentaciones](13_PRESENTATION_SOURCE_OF_TRUTH.md) | Narrativa oficial para decks y demos ejecutivas. |
| [Caso Nalub real](14_NALUB_REAL_CASE.md) | Caso tecnico secundario con MariaDB read-only. |
| [Integracion con Fabric y Databricks](15_INTEGRACION_FABRIC_DATABRICKS.md) | Como interpreta cada plataforma la ontologia, que archivos importables genera ONTO, cobertura/ruta y plan de conectores. |
| [Casos de prueba](casos/README.md) | Origenes de cada caso (comercial, distribuido, Nalub, Fabric SIC) para regenerarlos desde cero: que cargar en Atlas y resultado esperado. |

El caso Nalub usa `docs/casos/nalub_mariadb/` (esquema MariaDB sin datos y documento funcional/tecnico). La ejecucion validada produce 33 tablas, 255 columnas, 25 relaciones y 451 candidatos. El runner es `python scripts/run_nalub_case.py`; su release declara cinco consultas MariaDB y `--live` ejecuta validaciones read-only contra el perfil indicado.

Ver tambien la [guia del caso Nalub](14_NALUB_REAL_CASE.md).

## Principio de interoperabilidad

ONTO usa un modelo canonico intermedio y versionado para relevar y validar. Fabric, Databricks u otras plataformas pueden ser fuentes de datos, fuentes de evidencia, modelos semanticos y, sobre todo, el destino preferido donde se implementa la ontologia aprobada. ONTO no compite con esas plataformas: solo sostiene por su cuenta lo que no pueden implementar (plan B). Se conectan mediante adapters y contratos especificos para cada rol.

La documentacion debe responder siempre dos preguntas separadas:

1. Desde donde se leen metadata o datos operativos (uno o varios sistemas por dominio).
2. Donde se conserva o publica la ontologia aprobada.

## Decision de arquitectura

La implementacion local sigue siendo un monolito Streamlit. La separacion entre Atlas, Nexo y Argos es de contratos, artefactos, navegacion y responsabilidades (`onto_ui/atlas.py`, `onto_ui/nexo.py`, `onto_ui/argos.py`), no de servicios desplegables.

Durante el MVP, los tres productos son separables por contrato, datos y navegacion, pero viven en una sola aplicacion web monolitica que usa carpetas y persistencia locales. No se introduce infraestructura distribuida antes de que el piloto demuestre que hace falta.

La documentacion es intencionalmente independiente del caso ACC. El patron de investigador con evidencia puede inspirar el producto Runtime, pero ONTO no incorpora conocimiento, datos ni codigo del dominio de ciberseguridad.
