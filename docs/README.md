# Documentacion de producto

Esta carpeta es la fuente de verdad de ONTO, un acelerador para obtener una ontologia revisable a partir de informacion existente. Atlas, Nexo y Argos conservan responsabilidades separadas dentro de la misma aplicacion; no es necesario configurar tres productos para empezar.

**Entrada recomendada:** en Atlas, indicar un ambito, cargar los archivos disponibles y accionar Generar borrador de ontologia. Ver [recorrido simple y limites](05_ATLAS_ASSESSMENT_MVP.md#entrada-simple-de-archivos-a-borrador). El relevamiento detallado anterior sigue disponible como opcion avanzada.

**Continuidad del trabajo:** [Metodo de trabajo iterativo](17_METODO_DE_TRABAJO_ITERATIVO.md). Como actualizar o ampliar sin perder aprobaciones y rechazos, revisar cambios, consultar versiones y empezar de cero de forma explicita.

## Por donde empezar

1. [**Guia completa del producto**](ONTO_GUIA_COMPLETA_DEL_PRODUCTO.md) ([PDF](../deliverables/ONTO_Guia_Completa_del_Producto.pdf)): que es ONTO, para que sirve, que valor agrega, como piensa, como trabaja y como se integra con Fabric, Databricks y lo que el cliente ya tiene. Para perfiles de negocio y tecnicos.
2. [Objetivo, alcance y foco](OBJETIVO_ALCANCE_Y_FOCO.md): para que existe ONTO, que problema resuelve (dominios con datos distribuidos en varios sistemas), que incluye hoy y que no.
3. [Guia paso a paso no tecnica](GUIA_PASO_A_PASO_NO_TECNICA.md): ONTO explicado para negocio y gerencia, con el recorrido completo en lenguaje simple.
4. [MVP operativo de ONTO](00_MVP_OPERATIVO.md): como trabajar con la release local actual, proyectos validados y limites.
5. [Plan de reposicionamiento](18_PLAN_REPOSICIONAMIENTO.md): estado actual y pasos futuros.

| Documento | Proposito |
| --- | --- |
| [Guia completa del producto](ONTO_GUIA_COMPLETA_DEL_PRODUCTO.md) | Explicacion integral del producto para cualquier perfil. |
| [Plan de reposicionamiento](18_PLAN_REPOSICIONAMIENTO.md) | Posicionamiento, objetivos, fases, estado y pendientes. |
| [Piloto de validacion en plataformas](pilotos/PILOTO_VALIDACION_PLATAFORMAS.md) | Plantilla para probar los paquetes en Fabric y Databricks reales. |
| [Objetivo, alcance y foco](OBJETIVO_ALCANCE_Y_FOCO.md) | Documento de entrada: objetivo, problema, foco, alcance y metricas de exito. |
| [Guia paso a paso no tecnica](GUIA_PASO_A_PASO_NO_TECNICA.md) | Explicacion sin tecnicismos para comunicar ONTO a personas de negocio. |
| [MVP operativo](00_MVP_OPERATIVO.md) | Fuente de verdad para trabajar con la release local actual. |
| [Diagnostico y transformacion](01_DIAGNOSTICO_Y_TRANSFORMACION.md) | Explica el estado real del MVP, las brechas y que se conserva o transforma. |
| [PRD de Ontology Factory](02_PRD_ONTOLOGY_FACTORY.md) | Define problema, usuarios, productos, contratos, alcance y criterios de exito. |
| [Plan de alto nivel](03_PLAN_ALTO_NIVEL.md) | Ordena las fases, entregables, dependencias y gates de decision. |
| [Decision de arquitectura MVP](04_DECISION_ARQUITECTURA_MVP.md) | Fija el monolito web local como limite intencional de esta etapa. |
| [Atlas - Assessment MVP](05_ATLAS_ASSESSMENT_MVP.md) | Contrato y alcance del Producto 1 en el MVP operativo. |
| [Nexo - Registry & Validation MVP](06_NEXO_REGISTRY_MVP.md) | Contrato y alcance del Producto 2 en el MVP operativo. |
| [Argos - Runtime & Evaluation MVP](07_ARGOS_RUNTIME_MVP.md) | Contrato, límites y batería de evaluación del Producto 3 (banco de prueba). |
| [Interoperabilidad MVP](08_INTEROPERABILIDAD_MVP.md) | Planos de datos y ontologico; paquetes locales para Fabric y Databricks. |
| [Politica de datos demo](09_DEMO_DATA_POLICY.md) | Reglas para ejemplos, pilotos y artefactos locales. |
| [Posicionamiento y limites](10_POSITIONING_AND_BOUNDARIES.md) | Mensaje publico, productos, limites y anti-promesas. |
| [Estrategia de exportacion e interoperabilidad](11_EXPORT_AND_INTEROPERABILITY_STRATEGY.md) | Separacion entre fuentes de datos, modelos ontologicos y destinos. |
| [Demo end-to-end](12_DEMO_END_TO_END.md) | Guion del presentador: relato, cargas, motivos, brechas intencionales, validaciones y contingencias del caso distribuido. |
| [Fuente de verdad para presentaciones](13_PRESENTATION_SOURCE_OF_TRUTH.md) | Narrativa oficial para decks y demos ejecutivas. |
| [Caso Nalub real](14_NALUB_REAL_CASE.md) | Caso tecnico secundario con MariaDB read-only. |
| [Integracion con Fabric y Databricks](15_INTEGRACION_FABRIC_DATABRICKS.md) | Como interpreta cada plataforma la ontologia, que archivos importables genera ONTO (Fabric TMDL, Databricks, OWL/Ossie), cobertura/ruta y fases. |
| [Plan Atlas: cobertura explicativa](16_PLAN_ATLAS_COBERTURA_EXPLICATIVA.md) | Cinco partes implementables y comprobables para medir que entendemos, que falta y como avanzar entre assessments. |
| [Metodo de trabajo iterativo](17_METODO_DE_TRABAJO_ITERATIVO.md) | Forma de uso: version activa, continuidad de decisiones, regeneracion de pendientes, cambios e historial. |
| [Casos de prueba](casos/README.md) | Origenes de cada caso (comercial, distribuido, Nalub, Fabric SIC) para regenerarlos desde cero: que cargar en Atlas y resultado esperado. |

El caso Nalub usa `docs/casos/nalub_mariadb/` (esquema MariaDB sin datos y documento funcional/tecnico). La ejecucion validada produce 33 tablas, 255 columnas, 25 relaciones y 451 candidatos. El runner es `python scripts/run_nalub_case.py`; su release declara cinco consultas MariaDB y `--live` ejecuta validaciones read-only contra el perfil indicado.

Ver tambien la [guia del caso Nalub](14_NALUB_REAL_CASE.md).

## Demo y validacion manual

Guion completo para presentar ante publico: [documento editable](12_DEMO_END_TO_END.md) y [PDF del presentador](../deliverables/ONTO_Guion_Demo_Ventas_Distribuidas.pdf). Se regenera con `python scripts/build_demo_pdf.py` despues de instalar las dependencias.

La [guia de validacion manual del mismo caso](casos/ventas_distribuidas/README.md#validacion-manual-desde-cero-2026-10-07), preparada para la sesion del 2026-10-07, permite repetir ventas distribuidas desde el inicio, paso a paso, sin runners ni aprobaciones automaticas. Especifica archivos, proyecto nuevo sin resultados heredados, controles de scanner/Atlas/inferencias/Nexo/Argos/entrega y registro de observaciones. Conservar la ejecucion anterior para comparar y registrar los IDs y resultados propios de cada nueva sesion.

## Principio de interoperabilidad

ONTO usa un modelo canonico intermedio y versionado para relevar y validar. Fabric, Databricks u otras plataformas pueden ser fuentes de datos, fuentes de evidencia, modelos semanticos y, sobre todo, el destino preferido donde se implementa la ontologia aprobada. ONTO no compite con esas plataformas: solo sostiene por su cuenta lo que no pueden implementar (plan B, congelado como excepcion). Se conectan mediante adapters y contratos especificos para cada rol.

La documentacion debe responder siempre dos preguntas separadas:

1. Desde donde se leen metadata o datos operativos (uno o varios sistemas por dominio).
2. Donde se conserva o publica la ontologia aprobada.

## Decision de arquitectura

La implementacion local sigue siendo un monolito Streamlit. La separacion entre Atlas, Nexo y Argos es de contratos, artefactos, navegacion y responsabilidades (`onto_ui/atlas.py`, `onto_ui/nexo.py`, `onto_ui/argos.py`), no de servicios desplegables.

Durante el MVP, los tres productos son separables por contrato, datos y navegacion, pero viven en una sola aplicacion web monolitica que usa carpetas y persistencia locales. No se introduce infraestructura distribuida antes de que el piloto demuestre que hace falta.

La documentacion es intencionalmente independiente del caso ACC. El patron de investigador con evidencia puede inspirar el producto Runtime, pero ONTO no incorpora conocimiento, datos ni codigo del dominio de ciberseguridad.
