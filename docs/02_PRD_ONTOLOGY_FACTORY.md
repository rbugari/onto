# PRD - DataIA Ontology Factory

Fecha: 2026-08-01  
Estado: borrador base para validacion de producto  
Producto: ONTO

## 1. Problema

Las organizaciones disponen de modelos BI, warehouse/lakehouse, queries, procesos y documentacion que contienen conocimiento valioso, pero esta disperso, es desigual y rara vez esta listo para agentes. La dificultad no es solo documentar activos: es determinar que es confiable, convertirlo en conocimiento semantico validado y usarlo despues sin que un agente invente relaciones o consulte fuentes indebidas.

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

La Factory se entrega inicialmente como una aplicacion Streamlit monolitica que se ejecuta localmente. Usa `data/` para archivos y workspaces de ejecucion, SQLite local para indices o decisiones cuando haga falta y `.env` para configuracion de conectores y LLM.

No son requisitos del MVP: microservicios, API interna, cloud hosting, SSO, multi-tenancy real, colas, contenedores, base de datos gestionada ni sincronizacion continua con Fabric o Databricks. La separacion entre Assessment, Registry y Runtime es de contrato, datos, navegacion y pruebas.

La decision completa y sus criterios de salida estan en la [Decision de arquitectura MVP](04_DECISION_ARQUITECTURA_MVP.md).

## 5. Producto 1 - Atlas: Ontology Readiness Assessment

### Objetivo

Inventariar y evaluar el nivel de preparacion ontologica de un cliente, dominio o data product. **Atlas** representa la cartografia inicial de activos, contexto, evidencia y gaps.

### Entradas

- modelos Power BI/Fabric: inicialmente `model.bim`, despues PBIP, TMDL y API autorizada;
- metadata Databricks y otras plataformas mediante adapters;
- tablas, DDL, queries, catalogos, procesos y documentacion;
- ontologias o catalogos ya existentes del cliente, si los hubiera;
- configuracion de cliente, dominio, data product y politicas de analisis.

### Capacidades MVP

- alta de assessment y ejecuciones reproducibles;
- inventario de fuentes y archivos con hash, parser y estado;
- extraccion normalizada de metadata tecnica y contexto documental;
- deteccion de cobertura, definiciones ausentes, conflictos, ownership incompleto y riesgos;
- score determinista con evidencia y backlog priorizado;
- exportacion de `assessment package`.

### Salida contractual

```text
assessment-package/
  manifest.json
  semantic_inventory.json
  business_context_inventory.json
  source_inventory.json
  readiness_score.json
  gap_backlog.json
  evidence/
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
- workflow `draft -> pending_review -> approved/rejected -> deprecated`;
- comparacion de versiones y decisiones de revision;
- generacion de `agent_context_pack` y paquetes de publicacion;
- importacion y mapping de una ontologia externa existente.

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

## 8. Interoperabilidad

Fabric y Databricks se implementan como adapters de importacion, mapping y publicacion. Cada adapter debe declarar capacidades, limitaciones, autenticacion requerida y nivel de fidelidad.

Las operaciones se clasifican como:

- **Importar**: traer metadata u ontologia existente como evidencia y candidato.
- **Mapear**: relacionar elementos canonicos con objetos de plataforma sin publicar cambios.
- **Publicar**: generar o actualizar una representacion externa solo desde elementos aprobados.

Una publicacion exige release inmutable, mapping aprobado, identidad autorizada, manifest de despliegue, log y rollback logico.

## 9. Metricas de exito

- Porcentaje de activos inventariados con parser y evidencia.
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
