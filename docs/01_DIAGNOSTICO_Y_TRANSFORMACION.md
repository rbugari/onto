# Diagnostico y transformacion de ONTO

Fecha: 2026-09-30
Estado: diagnóstico y cierre del MVP operativo local

## 1. Punto de partida

ONTO es un MVP operativo local de Streamlit. Permite crear proyectos, registrar varios sistemas por dominio, importar su metadata, cargar documentos, ejecutar un scanner LLM/heuristico, generar diagnósticos Atlas, validar conocimiento en Nexo y consultarlo en Argos. Los proyectos `fabric-gold-sic-risk-pilot` y `commercial-sales-demo` demuestran el flujo completo; `distribuidora-ventas-distribuidas` demuestra Atlas sobre un dominio repartido en cinco sistemas; `nalub-case` funciona como validacion tecnica secundaria.

La implementacion actual es un MVP funcional de una Ontology Factory local. Mezcla en una misma aplicacion el modelado manual, el scanner documental y la persistencia orientada a proyecto, pero ya separa contratos de ejecucion, revision, releases, conectores y publicacion preparada.

## 2. Que se conserva

| Activo actual | Valor que se conserva | Transformacion necesaria |
| --- | --- | --- |
| Importador `model.bim` | Primer adaptador de metadata semantica Power BI | Ya convive con TMDL, PBIP, DDL generico y CSV de `information_schema`; falta cobertura de roles, jerarquias, DAX y lineage. |
| Scanner de documentos | Extrae terminos, definiciones, reglas y KPIs con chunks y evidencia | Ampliar citas por pagina/seccion, deduplicacion y controles de calidad. |
| Conceptos y relaciones | Base del modelo canónico curable | Profundizar la generación asistida y la revisión de impacto, sin aprobar inferencias automáticamente. |
| Exportaciones JSON/Markdown | Portabilidad inicial del workbench | Mantener paquetes versionados, context packs y mappings locales; falta publicación externa controlada. |
| Snapshots | Historial de trabajo local | Convivir con releases locales reconstruibles y fortalecer la estrategia de control de versiones. |

## 3. Brechas que deben resolverse primero

### Fundaciones tecnicas

- El repositorio Git existe, pero todavía no hay una estrategia de releases de producto ni CI/CD obligatoria.
- Los artefactos nuevos usan identificadores con UUID; los artefactos historicos pueden conservar ids antiguos y deben tratarse como evidencia local, no como contrato de unicidad futuro.
- Atlas ya organiza cada diagnostico por cliente, dominio, data product y `run_id`, con varios sistemas y casos de uso por proyecto; el proyecto local sigue siendo la unidad de trabajo de la interfaz.
- La validacion estructural ya se complementa con evidencia, ownership, revisión y releases locales; falta validación semántica de negocio más profunda.
- Las pruebas cubren el flujo local principal, pero falta ampliar contratos de conectores, permisos y regresiones de persistencia.

### Brechas de producto

- Los importadores cubren `model.bim`, TMDL, PBIP, DDL generico y CSV de `information_schema`; aun no cubren roles, jerarquias, anotaciones, dependencias DAX ni lineage.
- El mapa entre sistemas es heuristico (nombres normalizados y claves); las equivalencias no se confirman todavia como decision de Nexo.
- El scanner de contexto (antes Tool 02) ya fragmenta documentos, conserva evidencia por chunk y deduplica por contenido en los runners Risk y Ventas; quedan como evolucion las citas consistentes por pagina/seccion y controles de calidad mas profundos.
- Nexo ya genera y valida candidatos, conserva decisiones y emite releases locales; falta generación asistida de estructuras canónicas y revisión de impacto.
- Atlas ya produce scoring basal y backlog de gaps; Argos consume context packs, se abstiene fuera de alcance, puede usar LLM y ejecuta consultas read-only nombradas en adapters locales.
- Fabric cuenta con descubrimiento de metadata, bindings y consultas read-only nombradas; MariaDB ya tiene adapter live para Nalub. Databricks y otras plataformas se inventarian por archivo exportado. Fabric y Databricks solo disponen de mappings locales, sin publicación externa.

## 4. Arquitectura objetivo

La plataforma se divide en tres productos que comparten contratos. En este MVP se presentan como tres areas de una misma aplicacion web monolitica; no se despliegan como servicios separados:

1. **Ontology Readiness Assessment** descubre activos y mide madurez.
2. **Ontology Registry & Validation** transforma evidencia en una ontologia aprobada y versionada.
3. **Ontology Runtime** utiliza una release aprobada para responder o investigar con fuentes gobernadas.

Los tres comparten cuatro capacidades transversales implementadas dentro del mismo proceso:

- identidad y tenancy: `client`, `domain`, `data_product`, `run_id` y roles de revision;
- evidencia y lineage: fuente, fragmento, hash, version de parser/configuracion y confianza;
- versionado: snapshots de trabajo y releases locales reconstruibles;
- interoperabilidad: importadores, mappings y publicadores de plataformas externas.

## 5. Modelo de autoridad e interoperabilidad

El producto mantiene un modelo canonico propio como **formato intermedio de trabajo**: permite relevar, validar y versionar el conocimiento sin depender de una API o preview de un proveedor, y entregarlo despues a la plataforma que elija el cliente. No pretende reemplazar la ontologia de esa plataforma.

La interoperabilidad debe analizarse en dos planos independientes:

- **Plano de datos:** repositorios, warehouses, lakehouses, tablas, vistas, queries y modelos semanticos que aportan metadata o datos operativos.
- **Plano ontologico:** repositorios donde se conserva, importa, mapea o publica conocimiento ontologico aprobado.

Una plataforma puede aparecer en ambos planos. Por ejemplo, Fabric puede aportar metadata y filas mediante su Warehouse, y tambien ser un destino para un mapping hacia Fabric IQ Ontology. Esos usos requieren adapters, permisos, evidencias y estados distintos.

Cada elemento canonico puede vincularse a una implementacion externa mediante estos campos conceptuales:

```text
data_system_of_record       # fabric | databricks | sql_server | snowflake | mysql | external
data_external_reference     # identificador y ruta de tabla, vista, query o semantic model
data_access_mode             # metadata | read_only_query | none
ontology_system_of_record   # onto | fabric_iq | databricks | external
ontology_external_reference # identificador del repositorio ontologico externo
ontology_sync_mode           # import | map | publish | controlled_bidirectional
ontology_mapping_status      # proposed | approved | rejected | stale
source_evidence              # documentos, modelos, consultas o decisiones que lo sustentan
review_status                # draft | pending_review | approved | deprecated
ontology_version             # release que lo contiene
```

Asi se soportan tres modos de autoridad ontologica, en este orden de preferencia y sin duplicar decisiones de negocio:

- **Nativo de plataforma (preferido)**: Fabric, Databricks u otra herramienta del cliente es el sistema de registro ontologico; ONTO conserva mapping, evidencia y ciclo de revision.
- **Federado (mixto)**: la plataforma implementa lo que puede y ONTO sostiene la parte que queda afuera, con una vista canonica y reglas de sincronizacion explicitas.
- **Privado (plan B)**: ONTO gobierna y sirve la ontologia solo cuando ninguna plataforma puede implementarla de forma viable.

El producto nunca debe copiar datos de negocio para publicar una ontologia si basta con metadata, binding o referencia autorizada. La consulta de datos operativos de Argos es otro contrato y no convierte automaticamente al repositorio de datos en repositorio ontologico.

## 6. Reordenamiento propuesto del repositorio

La migracion debe ser incremental. La estructura de destino orientativa es:

```text
streamlit_app.py           # unico punto de entrada web: proyecto, navegacion y administracion
onto_ui/                   # pantallas Atlas, Nexo y Argos (ya separadas)
src/ontology_workbench/
  assessment/              # modulos internos de ingesta, inventarios y scoring
  registry/                # modelo canonico, revision y releases
  runtime/                 # context packs, planes y gateways
  interoperability/        # adapters locales Fabric/Databricks
  shared/                  # contratos, evidencia y persistencia local
data/workspaces/           # inputs, ejecuciones, evidencia y outputs locales
tests/                     # pruebas del monolito, sus contratos y la interfaz
docs/
```

El codigo actual se migrara por capacidad, no mediante una reescritura inicial:

- `bim_importer.py` se convierte en el primer adapter de assessment.
- `context_scanner.py` pasa a ser parte del pipeline de conocimiento, no la autoridad final.
- `models.py`, `service.py` y `storage.py` se sustituyen gradualmente por contratos compartidos y persistencia versionada.
- `streamlit_app.py` permanece como punto de entrada del MVP; las pantallas ya viven en `onto_ui/` por producto, sin introducir un segundo frontend o una API interna.

## 7. Decisiones para la evolucion posterior

1. Seleccionar el primer dominio piloto y un conjunto de fuentes reales autorizado.
2. Definir el modelo canonico minimo y el vocabulario de estados de revision.
3. Definir el contrato de carpetas locales y evaluar SQLite solo si un indice o auditoria ligera lo justifica; la implementacion actual usa JSON y directorios.
4. Acordar la primera plataforma externa prioritaria: Fabric, Databricks o ninguna para el piloto.
5. Definir politica de LLM: proveedor, residencia, datos permitidos, retencion y evaluacion.
6. Acordar quien puede aprobar definiciones, reglas, mappings y releases.
