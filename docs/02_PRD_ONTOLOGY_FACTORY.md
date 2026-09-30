# PRD - DataIA Ontology Factory

Fecha: 2026-09-30
Estado: PRD del MVP operativo; capacidades actuales y evolucion posterior diferenciadas
Producto: ONTO

Resumen ejecutivo: [Objetivo, alcance y foco](OBJETIVO_ALCANCE_Y_FOCO.md).

## 1. Problema

Las organizaciones disponen de modelos BI, warehouse/lakehouse, queries, procesos y documentacion que contienen conocimiento valioso, pero esta disperso, es desigual y rara vez esta listo para agentes. La dificultad no es solo documentar activos: es determinar que es confiable, convertirlo en conocimiento semantico validado y usarlo despues sin que un agente invente relaciones o consulte fuentes indebidas.

El caso dificil es el dominio **distribuido**: la misma entidad (cliente, producto, venta) vive en varios sistemas y plataformas con nombres y claves distintas. Si todo estuviera en una sola plataforma, sus herramientas nativas alcanzarian; cuando no, hace falta una ontologia comun que explique el dominio completo y que despues se implemente en la plataforma elegida.

## 2. Vision

ONTO convierte activos tecnicos y documentacion de una organizacion en conocimiento ontologico gobernado y utilizable. La plataforma entrega tres productos independientes:

1. un assessment de readiness ontologico;
2. una ontologia validada, versionada y portable;
3. un Runtime generico capaz de usar esa ontologia con evidencia y abstencion.

## 3. Usuarios y necesidades

| Usuario | Necesidad principal |
| --- | --- |
| Consultor/a Data & AI | Diagnosticar rapido activos, gaps y prioridades sin prometer una ontologia inexistente. |
| Arquitecto/a de datos | Entender fuentes, modelos, lineage, ownership y compatibilidad de plataformas. |
| Referente de negocio | Validar terminos, KPIs, reglas y conflictos en un formato comprensible. |
| Data steward / governance | Aprobar cambios, conservar evidencia y decidir el sistema de registro. |
| Equipo de agentes | Consumir una release y sus fuentes permitidas sin reconstruir el contexto en cada proyecto. |

## 4. Principios no negociables

- **Evidencia antes que inferencia**: toda propuesta debe conservar fuente y razon de confianza.
- **LLM propone; personas y reglas aprueban**: ningun LLM publica una definicion o binding por si solo.
- **Separacion de productos**: assessment, registry y runtime se comunican por contratos versionados.
- **Portabilidad sin dependencia**: el modelo canonico no se ata a Fabric ni Databricks.
- **Minimo privilegio**: se trabaja con metadata por defecto; los conectores de datos son read-only y explícitamente gobernados.
- **No responder es una capacidad**: el Runtime declara falta de evidencia, permisos o granularidad.
- **No duplicar datos**: la ontologia referencia activos y contratos autorizados; no replica datos de negocio innecesariamente.
- **Monolito primero**: durante el MVP, los productos viven en una unica aplicacion web local; los contratos los separan sin crear infraestructura distribuida.

## 4.1 Arquitectura de entrega MVP

La Factory se entrega inicialmente como una aplicacion Streamlit monolitica que se ejecuta localmente. Usa `data/` para archivos, releases y ejecuciones; JSON y directorios son la persistencia actual. SQLite queda como opcion futura para indices o auditoria ligera. `.env` y perfiles por proyecto contienen la configuracion local de conectores y LLM.

No son requisitos del MVP: microservicios, API interna, cloud hosting, SSO, multi-tenancy real, colas, contenedores, base de datos gestionada ni sincronizacion continua con Fabric o Databricks. La separacion entre Assessment, Registry y Runtime es de contrato, datos, navegacion y pruebas.

La decision completa y sus criterios de salida estan en la [Decision de arquitectura MVP](04_DECISION_ARQUITECTURA_MVP.md).

## 4.2 Flujo de trabajo del MVP

La interfaz presenta una ruta comun para todos los proyectos: **Atlas prepara evidencia**, **Nexo valida conocimiento** y **Argos investiga el negocio**. El usuario cambia de producto dentro del mismo proyecto; no necesita conocer las carpetas ni los contratos internos para completar el flujo.

## 5. Producto 1 - Atlas: Ontology Readiness Assessment

### Objetivo

Inventariar y evaluar el nivel de preparacion ontologica de un cliente, dominio o data product, aunque sus datos esten repartidos en varios sistemas. **Atlas** representa la cartografia inicial de activos, contexto, evidencia, cruces entre sistemas y gaps.

### Entradas

- varios sistemas por dominio, cada uno con plataforma, responsable y formato;
- modelos Power BI/Fabric: `model.bim`, TMDL, paquetes PBIP ZIP y payloads JSON semanticos compatibles;
- metadata de Databricks, SQL Server, PostgreSQL, Snowflake, Oracle, MariaDB o planillas mediante DDL (`.sql`) o CSV de `information_schema.columns`;
- metadata de Fabric por conexion directa de solo lectura;
- documentacion funcional: glosarios, KPIs, procesos, diccionarios;
- casos de uso con pregunta de negocio, responsable, prioridad y sistemas involucrados;
- configuracion de cliente, dominio y data product.

### Capacidades MVP

- alta de assessment y ejecuciones reproducibles;
- registro de sistemas e inventario por sistema, con archivo, hash y estado;
- extraccion normalizada de metadata tecnica y contexto documental;
- mapa de entidades compartidas entre sistemas y deteccion de claves comunes;
- deteccion de cobertura, definiciones ausentes, sistemas sin metadata o sin responsable y cruces sin clave;
- score determinista con evidencia y backlog priorizado por caso de uso;
- exportacion de `assessment package`.

### Salida contractual

```text
assessment-package/
  manifest.json
  scope_definition.json
  semantic_inventory.json
  business_context_inventory.json
  source_inventory.json
  cross_source_map.json
  evidence_index.json
  readiness_score.json
  gap_backlog.json
  assessment_review.json
  execution_summary.md
```

### Fuera de alcance

No aprueba una ontologia, no publica en plataformas externas y no responde preguntas de negocio como agente final.

## 6. Producto 2 - Ontology Registry & Validation

### Objetivo

Transformar uno o varios assessment packages en una ontologia candidata, facilitar su validacion humana y emitir una release consultable y portable.

### Capacidades MVP

- modelo canonico de entidades, propiedades, relaciones, KPIs, reglas, sinonimos, restricciones y fuentes;
- generacion de candidatos a partir de metadata y contexto de negocio;
- evidencia por elemento, confidence score, conflictos y preguntas;
- workflow `pending_review -> approved/rejected` por candidato y elemento canonico;
- comparacion de versiones y decisiones de revision;
- generacion de `agent_context_pack` y paquetes de publicacion locales.

Evolucion posterior: estado `deprecated`, importacion y mapping de una ontologia externa existente y confirmacion de equivalencias entre sistemas como decision de Nexo.

### Salida contractual

```text
ontology-release/
  release_manifest.json
  canonical_ontology.json
  review_decisions.json
  evidence_index.json
  source_bindings.json
  interoperability_mappings.json
  agent_context_pack.json
  publication_packages/
```

### Criterio de aceptacion clave

Una release debe poder ser revisada sin leer el material bruto y cada elemento aprobado debe poder rastrearse hasta una fuente o decision humana.

## 7. Producto 3 - Ontology Runtime / Investigador generico

### Objetivo

Permitir que una persona o producto consulte una ontology release mediante lenguaje natural, con fuentes, operaciones y limites definidos por el dominio.

### Capacidades MVP

- carga de una release y de su context pack;
- interpretacion de pregunta con plan explicito;
- recuperacion de conocimiento y uso de conectores autorizados;
- gateway de consultas read-only con allowlists, limites y auditoria;
- respuestas con evidencia, limitaciones y confianza;
- abstencion explicita ante fuente no autorizada, evidencia insuficiente, permisos o grano incompatible;
- trazas separadas para audiencia de negocio y soporte tecnico.

### Fuera de alcance

No crea definiciones oficiales, no modifica sistemas fuente y no elude permisos de usuarios o plataformas.

## 8. Interoperabilidad en dos planos

Fabric, Databricks y otras plataformas pueden participar en dos planos diferentes. Cada adapter debe declarar explicitamente en cual opera, sus capacidades, limitaciones, autenticacion requerida y nivel de fidelidad.

### 8.1 Plano de datos

Incluye warehouses, lakehouses, bases SQL, tablas, vistas, queries y modelos semanticos. En este plano ONTO puede:

- importar metadata tecnica para Atlas, por conexion (Fabric) o por archivo exportado (Databricks y otros);
- importar un semantic model existente como evidencia y estructura tecnica;
- registrar bindings entre elementos aprobados y activos externos;
- ejecutar desde Argos operaciones read-only nombradas y parametrizadas.

Fabric es en este plano un repositorio de datos mas, igual que Databricks, Snowflake, SQL Server o MySQL. El acceso a datos operativos requiere permisos, limites, auditoria y un contrato de consulta independiente del contrato ontologico.

### 8.2 Plano ontologico

Incluye la ontologia canonica de ONTO y los repositorios ontologicos externos del cliente, como Fabric IQ Ontology, capacidades ontologicas de Databricks, Purview, Collibra, Neo4j o RDF/OWL.

En este plano ONTO puede:

- importar una ontologia existente como evidencia o candidato;
- mapear elementos canonicos aprobados hacia objetos ontologicos externos;
- generar un paquete de publicacion;
- publicar o actualizar una representacion externa solo mediante un adapter controlado.

La ontologia externa no sustituye automaticamente la release de ONTO. El sistema de registro, la version, el estado del mapping y la autoridad de cada elemento deben quedar declarados.

### 8.3 Operaciones

- **Importar datos o metadata:** traer evidencia desde un repositorio de datos o semantic model.
- **Importar ontologia:** traer una representacion ontologica externa para analizarla o mapearla.
- **Mapear:** relacionar elementos canonicos aprobados con objetos externos sin publicar cambios.
- **Publicar:** generar o actualizar una representacion externa solo desde una release aprobada.
- **Consultar:** ejecutar operaciones read-only autorizadas sobre fuentes de datos mediante Argos.

Una publicacion exige release aprobada, mapping aprobado, identidad autorizada, manifest de despliegue, log y rollback operativo. El MVP solo genera paquetes locales `ready_for_review` y no publica externamente.

## 9. Metricas de exito

- Porcentaje de activos inventariados con parser y evidencia.
- Porcentaje de sistemas del caso de uso inventariados y con responsable.
- Entidades compartidas entre sistemas con clave o regla de cruce documentada.
- Cobertura de definiciones, owners, reglas y lineage por dominio.
- Tiempo de pasar de fuentes brutas a una release revisable.
- Porcentaje de candidatos aceptados/rechazados y causas de rechazo.
- Porcentaje de respuestas Runtime con evidencia suficiente.
- Porcentaje de abstenciones correctas en la bateria de evaluacion.
- Numero de releases y mappings reproducibles por plataforma.

## 10. Riesgos de producto

| Riesgo | Mitigacion |
| --- | --- |
| Inferencias LLM excesivas | Evidencia obligatoria, estados de revision y evaluaciones de precision. |
| Fuentes pobres o contradictorias | Gaps y preguntas visibles; no forzar una definicion canonica. |
| Dependencia de previews de plataforma | Modelo canonico propio, adapters aislados y modo fallback. |
| Datos sensibles en prompts | Minimizacion de contexto, configuracion por cliente y politica de LLM. |
| Ontologia desactualizada | Releases, hash de fuentes, mappings stale y proceso de revalidacion. |
| Runtime con acceso excesivo | Bindings declarativos, identidad delegada cuando aplique y gateways read-only. |
