# Posicionamiento y limites

Estado: fuente normativa para producto, comunicacion y alcance del MVP

## Frase de posicionamiento

> ONTO prepara el conocimiento de negocio que las plataformas necesitan y no pueden generar solas: llega a Silver, cruza varios sistemas y lo entrega aprobado, listo para cargar.

Version larga: ONTO convierte evidencia tecnica y funcional existente en conocimiento ontologico gobernado, revisable y consumible por IA.

## Foco

Las capas semanticas y ontologias de las plataformas (modelos semanticos y Ontology de Fabric IQ, metric views y Genie Ontology de Databricks) parten de la capa Gold y de su propio ecosistema. ONTO aporta mas valor donde ellas no llegan:

- **Mas abajo de Gold:** entidades en Silver o Bronze, y sistemas fuera de la plataforma, que no tienen significado documentado.
- **Entre sistemas:** el dominio esta **repartido en varios sistemas y plataformas**. Atlas arma la vista completa (que sistemas participan, que entidades comparten, como se cruzan y que falta).
- **Contenido que alguien tiene que escribir:** definiciones, sinonimos, reglas y descripciones que las plataformas esperan pero no inventan. Nexo los produce desde evidencia, con aprobacion humana, en un formato portable para cargarlos en Fabric, Databricks u otra herramienta.

Cuando todo vive en una sola plataforma y esta en Gold, las herramientas nativas alcanzan y ONTO no intenta competir. Ver [Objetivo, alcance y foco](OBJETIVO_ALCANCE_Y_FOCO.md) y el [plan de reposicionamiento](18_PLAN_REPOSICIONAMIENTO.md).

## Relacion con Fabric, Databricks y otras plataformas ontologicas

**ONTO no compite con Fabric IQ Ontology, con las capacidades ontologicas de Databricks ni con otras herramientas del cliente.** Hace el trabajo previo que esas plataformas necesitan y no resuelven solas: relevar el dominio completo, cruzar sistemas, validar con evidencia y hacer aprobar el conocimiento por personas.

Orden de preferencia para implementar lo aprobado:

1. **Ruta A, nativa (por defecto):** se entrega el paquete y la plataforma del cliente lo implementa y lo gobierna.
2. **Ruta B, mixta:** la plataforma implementa lo que puede; ONTO sostiene solo la parte que queda afuera (fuentes que no alcanza, reglas que no soporta, costo o gobierno).
3. **Ruta C, plan B:** si ninguna plataforma puede implementarlo de forma viable, ONTO conserva la release y Argos la sirve.

Argos no es el destino buscado: es el banco de prueba del contexto aprobado. El plan B (ruta C) sigue funcionando como caso documentado, pero no recibe inversion nueva.

## Que hace ONTO

- inventaria modelos, metadata, documentacion y fuentes relevantes de todos los sistemas del dominio;
- detecta entidades compartidas entre sistemas y la falta de claves o equivalencias;
- conserva evidencia y trazabilidad;
- mide readiness y detecta gaps;
- genera candidatos ontologicos;
- facilita revision humana;
- emite releases locales reconstruibles, con identificadores y manifests;
- prepara bindings, context packs y mappings;
- permite consultar conocimiento aprobado con limites y abstencion;
- prepara mappings y paquetes de publicacion para herramientas del cliente; el MVP no publica externamente.

## Que no hace

- no reemplaza el warehouse, lakehouse, catalogo o gobierno de datos del cliente;
- no reemplaza Fabric, Databricks, Purview, Collibra, Neo4j u otra herramienta ontologica: les entrega el conocimiento preparado y solo cubre lo que no pueden implementar;
- no aprueba automaticamente inferencias de un LLM;
- no inventa una ontologia final sin evidencia y decision humana;
- no acepta SQL libre desde Argos;
- no modifica sistemas fuente en el MVP;
- no copia datos de negocio si basta con metadata, binding o referencia autorizada.

## Productos

El flujo de trabajo del MVP es comun a todos los proyectos: Atlas prepara evidencia, Nexo valida conocimiento y Argos investiga el negocio. La diferencia entre proyectos esta en los sistemas, fuentes y catalogos autorizados, no en la arquitectura ni en las reglas de gobierno.

### Atlas

Assessment de readiness ontologico. Descubre activos, evidencia, cobertura, gaps, riesgos y prioridades. No aprueba ni publica una ontologia.

### Nexo

Registry y validacion. Convierte evidencia en candidatos revisables, conserva decisiones y emite una release canonica aprobada. Puede preparar mappings o paquetes de publicacion.

### Argos

Banco de prueba. Usa una release aprobada para probar que el contexto responde bien antes de implementarlo en la plataforma. Responde con evidencia, consulta fuentes autorizadas y se abstiene cuando faltan evidencia, permisos o granularidad. Su uso como runtime de plan B esta congelado (ver [MVP operativo](00_MVP_OPERATIVO.md)).

## Dos planos

- **Plano de datos:** Fabric, Databricks, Snowflake, SQL Server, MySQL, semantic models y otras fuentes aportan metadata o datos operativos.
- **Plano ontologico:** ONTO, Fabric IQ Ontology, Databricks u otras herramientas conservan o reciben conocimiento ontologico aprobado.

Una plataforma puede participar en ambos planos, pero no se debe confundir de donde se leen datos con donde se conserva la ontologia.

## Anti-promesas

Evitar:

- “ONTO organiza todos los datos de la empresa”.
- “ONTO reemplaza el catalogo o el gobierno de datos”.
- “ONTO crea automaticamente la ontologia final”.
- “ONTO funciona solo con Fabric”.
- “ONTO es un agente o runtime de preguntas de negocio” (es el banco de prueba de lo que se entrega).
- “ONTO es una alternativa a la ontologia de Fabric o de Databricks” (las prepara y complementa; no compite).
- “Con ONTO no hace falta implementar en la plataforma” (la ruta por defecto es implementar en la plataforma del cliente).
- “ONTO se conecta en vivo a Databricks” (hoy se carga por archivo exportado).
- “ONTO resuelve automaticamente las equivalencias entre sistemas” (las detecta; las confirman personas).
- “ONTO garantiza respuestas correctas fuera de la evidencia aprobada”.
