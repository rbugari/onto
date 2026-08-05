# Plan de alto nivel - ONTO

Fecha: 2026-08-01  
Estado: Fase 1 en ejecucion; secuencia para un monolito web local. Las estimaciones se definiran tras seleccionar piloto.

## Resultado esperado

Construir de forma incremental los tres productos de Ontology Factory sin bloquear el valor temprano: primero se obtiene un assessment repetible, despues una ontologia revisable y finalmente un investigador generico sobre releases aprobadas.

## Fase 0 - Fundaciones y decision de piloto

**Objetivo:** convertir el MVP actual en una base segura para evolucionar.

- Inicializar control de versiones, convenciones de ramas y validacion automatica.
- Corregir IDs de documentos/snapshots y aislar datos de demo.
- Definir `client/domain/data_product/run_id`, estados, roles y contrato de evidencia.
- Fijar Streamlit, carpetas locales, SQLite opcional y `.env` como arquitectura unica del MVP.
- Seleccionar un dominio piloto, fuentes autorizadas y criterios de evaluacion.
- Elegir proveedor LLM y su politica local de datos; no crear infraestructura compartida.

**Gate:** contrato comun aprobado y un conjunto de input representativo disponible.

## Fase 1 - Atlas Assessment MVP

**Objetivo:** producir un assessment package reproducible a partir de fuentes reales.

- Extraer el importador BIM como adapter y normalizar su salida.
- Introducir manifest de fuentes, hashes, parser version y errores de ingesta.
- Ampliar Tool 2: el MVP ya fragmenta documentos y conserva citas de chunk; faltan deduplicacion avanzada, citas por pagina/seccion y controles LLM mas profundos.
- Definir reglas deterministas iniciales de readiness y gap backlog.
- Generar artefactos de salida JSON/Markdown/Excel o equivalente de revision.

**Entregable:** un assessment package de un dominio piloto, con inventario, contexto, score y gaps.

El primer corte ya implementado genera el paquete local con manifest, inventarios, hashes de documentos, indice de evidencia por fragmentos, score basal, backlog y checkpoint humano de revision. El adaptador `model.bim` conserva ahora el archivo original local y su hash cuando se importa por la aplicacion. Las siguientes iteraciones amplian adapters, citas por pagina/seccion y calidad del scoring.

Situacion demostrada con `risk1`: el assessment es repetible y conserva 19 fragmentos de evidencia. El primer scanner heuristico produjo 104 definiciones candidatas; el scanner posterior con el proveedor compartido GPT-5.6 produjo 35 definiciones, 51 reglas y 33 KPIs, todos trazables por chunk. Tambien deja visibles las brechas reales: reimportar el `model.bim` original para capturar su evidencia, revisar candidatos y asignar ownership. No se debe promocionar ese proyecto a Registry hasta que la revision humana lo decida.

**Gate:** el equipo puede repetir una ejecucion con el mismo input y explicar cada score o gap con evidencia.

## Fase 2 - Registry y validacion ontologica

**Objetivo:** convertir assessment packages en ontology releases aprobables.

- Implementar el modelo canonico minimo y su persistencia versionada.
- Generar entidades, propiedades, relaciones, KPIs y reglas candidatas.
- Construir la cola de revision humana y el registro de decisiones.
- Implementar conflictos, sinonimos, ownership, source bindings y lineage minimo.
- Emitir release inmutable, context pack y artefactos de revision.

**Entregable:** primera ontology release de un dominio piloto, con evidencia y decisiones de validacion.

**Gate:** un referente de negocio y uno tecnico pueden aceptar/rechazar cambios y la release puede reconstruirse desde sus manifiestos.

Tercer corte implementado: Nexo crea un draft desde Atlas, conserva candidatos y decisiones por separado y bloquea la emisión de una release hasta que todos los candidatos y elementos del modelo sean revisados. Propone consolidaciones exactas o semánticas, permite revisiones masivas y puede aplicar una consolidación aceptada sin aprobar implícitamente el candidato canónico. El draft permite curar y aprobar propiedades, relaciones, sinónimos y restricciones, con responsable y vínculos trazables a candidatos aprobados. También compara un draft contra una release o dos releases entre sí, señalando altas, bajas y cambios semánticos sin alterar los artefactos. La siguiente iteración debe sumar generación asistida de estructuras canónicas y una revisión de impacto más rica, sin convertir inferencias en aprobaciones automáticas.

## Fase 3 - Interoperabilidad inicial

**Objetivo:** demostrar que el modelo canonico coexiste con una plataforma del cliente.

- Priorizar un adapter (Fabric o Databricks) a partir del piloto.
- Implementar importacion o mapping de metadata/ontologia existente.
- Generar paquete de publicacion desde una release aprobada.
- Registrar capacidades, prerequisitos, deployment manifest y rollback logico.

**Entregable:** mapping validado o publicacion controlada en una plataforma, sin duplicar datos de negocio.

**Gate:** se puede identificar sistema de registro, version y estado de sincronizacion de cada elemento publicado.

Primer corte implementado: una release aprobada puede generar un paquete local de interoperabilidad para Microsoft Fabric o Databricks. El paquete contiene mapping de entidades, reglas, KPIs y estructuras canónicas, manifest de despliegue y rollback lógico. Su estado es `ready_for_review` y su modo es `local_mapping_only`: no usa credenciales, no transporta datos de negocio ni ejecuta publicaciones externas. El siguiente corte de esta fase requiere elegir un destino real y definir su adapter de autenticación, workspace, bindings y publicación controlada.

## Fase 4 - Runtime / Investigador generico MVP

**Objetivo:** usar una ontology release como contexto gobernado para consultas reales.

- Definir contrato de pregunta, plan, evidencia, respuesta y abstencion.
- Cargar context packs y source bindings aprobados.
- Implementar gateway read-only para el primer tipo de fuente.
- Crear bateria de preguntas respondibles, no respondibles y de grano incompatible.
- Separar vista funcional y traza tecnica; registrar auditoria util para evaluacion.

**Entregable:** investigador funcional para un dominio piloto que responde solo dentro de los limites de la release.

**Gate:** la bateria valida evidencia, abstencion y autorizacion antes de ampliar cobertura.

Primer corte implementado: Argos consulta únicamente el `agent_context_pack` de una release local, devuelve los elementos recuperados y se abstiene cuando no encuentra evidencia. La aplicación puede preparar una batería base desde la release, editar sus casos y evaluar `answered`/`abstained` más la evidencia esperada. Cada evaluación deja su manifest, resumen y resultados por caso bajo `data/runtime/<project>/<release>/evaluations/`. Para el piloto Fabric actual, el gate se cierra dentro de la aplicación local usando metadata, bindings y mappings ya aprobados; el gateway read-only, los controles de permisos y los casos de grano incompatible quedan fuera de alcance hasta que el piloto demuestre valor con preguntas reales.

## Fase 5 - Evaluacion de evolucion posterior

**Objetivo:** decidir, con evidencia de uso, si corresponde elevar la arquitectura del PoC.

- Multi-tenancy, SSO, roles, auditoria y retencion formal si el piloto lo exige.
- Catalogo de adapters y pruebas de contrato.
- Observabilidad de ingestas, LLM, publicaciones y Runtime.
- Evaluaciones repetibles de calidad semantica y de agentes.
- Empaquetado, CI/CD y estrategia de despliegue solo si se aprueba continuidad.

## Dependencias y decisiones de orden

| Capacidad | Depende de | No debe anticiparse a |
| --- | --- | --- |
| Scoring de readiness | inventario, evidencia y reglas | una ontologia final |
| Generacion LLM de candidatos | contratos y fuentes trazables | publicacion automatica |
| Publicacion Fabric/Databricks | release y mapping aprobados | Runtime de produccion |
| Runtime generico | context pack y source bindings | acceso libre a datos |
| Multiusuario/produccion | piloto validado, modelo de autoridad y auditoria | demo local de piloto |

## Prioridad de las proximas acciones

1. Validar este PRD y seleccionar el dominio piloto.
2. Crear contrato de datos y evidencia compartido.
3. Estabilizar el MVP actual y convertirlo en Assessment MVP.
4. Definir el modelo canonico antes de comenzar pantallas complejas de revision.
