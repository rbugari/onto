# Plan de alto nivel - ONTO

Fecha: 2026-09-30
Estado: fases 0 a 4 cerradas como MVP operativo; Atlas ampliado a dominios multi-sistema; fase 5 reservada para evolucion posterior.

## Resultado esperado

El MVP operativo ya permite recorrer los tres productos de Ontology Factory: primero se obtiene un assessment repetible, despues una ontologia revisable y finalmente un investigador sobre releases aprobadas. El plan siguiente se limita a ampliar cobertura, gobierno e integraciones a partir del uso real.

## Fase 0 - Fundaciones y decision de piloto

**Objetivo:** convertir el MVP actual en una base segura para evolucionar.

- Inicializar control de versiones, convenciones de ramas y validacion automatica.
- Corregir IDs de documentos/snapshots y aislar datos de demo.
- Definir `client/domain/data_product/run_id`, estados, roles y contrato de evidencia.
- Fijar Streamlit, carpetas locales, JSON, perfiles por proyecto y `.env` como arquitectura unica del MVP; SQLite queda opcional para una etapa posterior.
- Seleccionar un dominio piloto, fuentes autorizadas y criterios de evaluacion.
- Elegir proveedor LLM y su politica local de datos; no crear infraestructura compartida.

**Gate:** contrato comun aprobado y un conjunto de input representativo disponible.

## Fase 1 - Atlas Assessment MVP

**Objetivo:** producir un assessment package reproducible a partir de fuentes reales.

- Extraer el importador BIM como adapter y normalizar su salida.
- Introducir manifest de fuentes, hashes, parser version y errores de ingesta.
- Ampliar el scanner de contexto (antes Tool 2): el MVP ya fragmenta documentos, conserva citas de chunk y deduplica documentos repetidos por contenido; quedan citas por pagina/seccion y controles LLM mas profundos.
- Definir reglas deterministas iniciales de readiness y gap backlog.
- Generar artefactos de salida JSON/Markdown/Excel o equivalente de revision.

**Entregable:** un assessment package de un dominio piloto, con inventario, contexto, score y gaps.

La implementacion del MVP genera el paquete local con manifest, inventarios, hashes de documentos, indice de evidencia por fragmentos, score basal, backlog y checkpoint humano de revision. El adaptador `model.bim` conserva el archivo original local y su hash cuando se importa por la aplicacion. La evolucion posterior amplia adapters, citas por pagina/seccion y calidad del scoring.

Situacion demostrada con `fabric-gold-sic-risk-pilot`: el assessment es repetible y conserva evidencia documental por chunk junto con metadata técnica Fabric. El scanner del piloto produjo candidatos trazables de conceptos, reglas y KPIs; el flujo `documentation-first` conserva los gaps y los matches ambiguos para revisión humana. Una release local aprobada alimenta la evaluación de Argos, pero cada nuevo assessment o cambio de negocio debe volver a revisarse antes de emitirse.

**Gate:** el equipo puede repetir una ejecucion con el mismo input y explicar cada score o gap con evidencia.

## Fase 2 - Registry y validacion ontologica

**Objetivo:** convertir assessment packages en ontology releases aprobables.

- Implementar el modelo canonico minimo y su persistencia versionada.
- Generar entidades, propiedades, relaciones, KPIs y reglas candidatas.
- Construir la cola de revision humana y el registro de decisiones.
- Implementar conflictos, sinonimos, ownership, source bindings y lineage minimo.
- Emitir release local reconstruible, context pack y artefactos de revision.

**Entregable:** primera ontology release de un dominio piloto, con evidencia y decisiones de validacion.

**Gate:** un referente de negocio y uno tecnico pueden aceptar/rechazar cambios y la release puede reconstruirse desde sus manifiestos.

La implementacion del MVP permite a Nexo crear un draft desde Atlas, conservar candidatos y decisiones por separado y bloquear la emisión de una release hasta que todos los candidatos y elementos del modelo sean revisados. Propone consolidaciones exactas o semánticas, permite revisiones masivas y puede aplicar una consolidación aceptada sin aprobar implícitamente el candidato canónico. El draft permite curar y aprobar propiedades, relaciones, sinónimos y restricciones, con responsable y vínculos trazables a candidatos aprobados. También compara un draft contra una release o dos releases entre sí, señalando altas, bajas y cambios semánticos sin alterar los artefactos. La evolucion posterior suma generación asistida de estructuras canónicas y una revisión de impacto más rica, sin convertir inferencias en aprobaciones automáticas.

**Estado de autoridad de fuente:** la autoridad configurable (`technical`, `documentation` o `hybrid`) ya está implementada. En `documentation-first`, la documentación define el universo funcional y los activos técnicos no documentados quedan fuera de los candidatos de negocio. El matching determinista entre documentación y metadata registra documento/chunk, activo vinculado, confianza, motivo y gaps sin binding. La revisión humana de resultados ambiguos sigue siendo obligatoria antes de emitir una release de negocio.

## Fase 3 - Interoperabilidad inicial

**Objetivo:** demostrar que el modelo canonico coexiste con una plataforma del cliente.

- Priorizar un adapter (Fabric o Databricks) a partir del piloto.
- Implementar importacion o mapping de metadata/ontologia existente.
- Generar paquete de publicacion desde una release aprobada.
- Registrar capacidades, prerequisitos, deployment manifest y rollback logico.

**Entregable:** mapping validado o publicacion controlada en una plataforma, sin duplicar datos de negocio.

**Gate:** se puede identificar sistema de registro, version y estado de sincronizacion de cada elemento publicado.

La implementacion del MVP permite que una release aprobada genere un paquete local de interoperabilidad para Microsoft Fabric o Databricks. El paquete contiene mapping de entidades, reglas, KPIs y estructuras canónicas, manifest de despliegue y queda en `ready_for_review` con modo `local_mapping_only`: no usa credenciales, no transporta datos de negocio ni ejecuta publicaciones externas. La evolucion posterior requiere elegir un destino real y definir su adapter de autenticación, workspace, bindings y publicación controlada.

## Fase 4 - Runtime / Investigador generico MVP

**Objetivo:** usar una ontology release como contexto gobernado para consultas reales.

- Definir contrato de pregunta, plan, evidencia, respuesta y abstencion.
- Cargar context packs y source bindings aprobados.
- Implementar gateway read-only para el primer tipo de fuente.
- Crear bateria de preguntas respondibles, no respondibles y de grano incompatible.
- Separar vista funcional y traza tecnica; registrar auditoria util para evaluacion.

**Entregable:** investigador funcional para un dominio piloto que responde solo dentro de los limites de la release.

**Gate:** la bateria valida evidencia, abstencion y autorizacion antes de ampliar cobertura.

La implementacion del MVP permite que Argos consulte el `agent_context_pack` de una release local, devuelva los elementos recuperados y se abstenga cuando no encuentra evidencia. La aplicación puede preparar una batería base desde la release, editar sus casos y evaluar `answered`/`abstained` más la evidencia esperada. La ruta LLM conserva la recuperación de evidencia y bloquea respuestas sin contexto aprobado o resultado live. Cada investigación deja manifest, request, retrieval, traceability y answer bajo `data/runtime/<project>/<release>/<investigation>/`; la UI puede reconstruir el historial persistido tras una recarga. Cada evaluación deja su manifest, resumen y resultados por caso bajo `data/runtime/<project>/<release>/evaluations/`. El caso Nalub valida en MariaDB pedidos, ventas y demanda de productos; los controles multiusuario y la autorización por usuario quedan fuera de alcance.

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

## Plan actualizado de trabajo

### Ya implementado

- Monolito local Streamlit con Atlas, Nexo y Argos separados por contrato.
- Assessment Atlas reproducible con evidencia, score basal y gaps.
- Draft y release Nexo con decisiones humanas, modelo canonico y context pack.
- Bindings y mappings locales para Fabric y Databricks.
- Argos con abstencion, evaluacion local y consultas read-only en adapters Fabric, local_synthetic y MariaDB.
- Query catalog configurable por release, con routing y parametros declarativos.
- Auditoria tecnica base de Argos por investigacion, con hash de pregunta, resultado del adapter, operacion, filas y declaracion de no persistencia de secretos.
- Demo comercial sintetica ejecutada con 3 tablas, 5 documentos, gaps, release, mapping y evaluacion Argos 2/2.
- Caso Nalub schema-first ejecutado con el backup MariaDB: 33 tablas, 255 columnas, 25 relaciones, 451 candidatos y 5 queries read-only declaradas. El runner live valida las consultas principales sobre MariaDB real.
- Distincion documental entre plano de datos y plano ontologico.
- Atlas multi-sistema: varios sistemas por proyecto, carga de metadata externa por DDL o CSV (Databricks, SQL Server, PostgreSQL, Snowflake, Oracle), mapa de entidades compartidas, dimension de alineacion entre sistemas y gaps por caso de uso. Demo `distribuidora-ventas-distribuidas` con cinco sistemas.
- Interfaz reorganizada: Atlas en cuatro pestanas guiadas, Nexo en cinco pestanas con revisor unico de sesion, Argos como conversacion con pestana de analistas; preguntas iniciales y graficos definidos por el catalogo.
- Pruebas de interfaz con `AppTest` sobre datos temporales.

### Pendiente prioritario

1. **Formalizar gobierno del piloto:** secretos y criterios de aprobacion; la politica LLM (`approved_external`/`local_only`), la auditoria tecnica base y el informe manual de retencion ya estan implementados. Multiusuario, roles y autorizacion quedan diferidos para una etapa posterior.
2. **Cerrar el ciclo multi-sistema:** que Nexo registre como decision las equivalencias entre sistemas detectadas por Atlas (clave comun o tabla de correspondencia) y que la release las incluya.
3. **Ampliar fuentes:** descubrimiento remoto de Databricks (Unity Catalog) y conexion autenticada a APIs de semantic models solo despues de estabilizar los contratos; hoy se cargan por archivo exportado.
4. **Elegir un destino ontologico real:** solo entonces implementar publicacion controlada, autenticacion, deployment y rollback efectivo.

### Gate para la siguiente etapa

La demo comercial ya produce una release y ejecuta una consulta parametrizada con filas desde `sales_by_customer`. El caso Nalub cerro el gate funcional contra MariaDB real: las cinco capacidades declaradas fueron ejecutadas, se verificaron limites y parametros, y se probaron abstenciones fuera de catalogo y ante SQL directo. El siguiente gate es gobierno y ampliacion de fuentes, no habilitar SQL libre.
