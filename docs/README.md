# Documentacion de producto

Esta carpeta define la reconversion de ONTO desde un MVP local de workbench a una **Ontology Factory** formada por tres productos independientes y conectables.

| Documento | Proposito |
| --- | --- |
| [Diagnostico y transformacion](01_DIAGNOSTICO_Y_TRANSFORMACION.md) | Explica el estado real del MVP, las brechas y que se conserva o transforma. |
| [PRD de Ontology Factory](02_PRD_ONTOLOGY_FACTORY.md) | Define problema, usuarios, productos, contratos, alcance y criterios de exito. |
| [Plan de alto nivel](03_PLAN_ALTO_NIVEL.md) | Ordena las fases, entregables, dependencias y gates de decision. |
| [Decision de arquitectura MVP](04_DECISION_ARQUITECTURA_MVP.md) | Fija el monolito web local como limite intencional de esta etapa. |
| [Atlas - Assessment MVP](05_ATLAS_ASSESSMENT_MVP.md) | Contrato y alcance del primer corte implementado del Producto 1. |
| [Nexo - Registry & Validation MVP](06_NEXO_REGISTRY_MVP.md) | Contrato y alcance del primer corte implementado del Producto 2. |
| [Argos - Runtime & Evaluation MVP](07_ARGOS_RUNTIME_MVP.md) | Contrato, límites y batería de evaluación del Producto 3. |
| [Interoperabilidad MVP](08_INTEROPERABILIDAD_MVP.md) | Paquetes locales de mapping para Fabric y Databricks. |

## Decision de arquitectura

ONTO tendra un modelo canonico propio y versionado. Fabric, Databricks u otras plataformas no son bifurcaciones del producto: son fuentes, sistemas de registro opcionales o destinos de publicacion conectados mediante adaptadores.

Durante el MVP, los tres productos son separables por contrato, datos y navegacion, pero viven en una sola aplicacion web monolitica que usa carpetas y persistencia locales. No se introduce infraestructura distribuida antes de que el piloto demuestre que hace falta.

La documentacion es intencionalmente independiente del caso ACC. El patron de investigador con evidencia puede inspirar el producto Runtime, pero ONTO no incorpora conocimiento, datos ni codigo del dominio de ciberseguridad.
