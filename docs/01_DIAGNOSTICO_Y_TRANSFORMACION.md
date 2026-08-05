# Diagnostico y transformacion de ONTO

Fecha: 2026-08-01  
Estado: decision de producto para la siguiente etapa

## 1. Punto de partida

ONTO es hoy un MVP local de Streamlit. Permite crear proyectos, mantener conceptos y relaciones, importar `model.bim`, cargar documentos, extraer texto, ejecutar un scanner LLM/heuristico y exportar JSON o Markdown. El ejemplo `risk1` prueba que puede manejar un modelo tabular real de tamano relevante.

La implementacion actual tiene valor como prueba de ingesta y exploracion, pero no representa todavia una Ontology Factory. Mezcla en una misma aplicacion el modelado manual, el scanner documental y una persistencia local orientada a proyecto, sin contratos de ejecucion, revision ni publicacion.

## 2. Que se conserva

| Activo actual | Valor que se conserva | Transformacion necesaria |
| --- | --- | --- |
| Importador `model.bim` | Primer adaptador de metadata semantica Power BI | Convertirlo en un adaptador Tool 01 con contrato normalizado, trazabilidad y cobertura ampliada. |
| Scanner de documentos | Base para extraer terminos, definiciones, reglas y ambiguedades | Introducir chunking, evidencia por fragmento, deduplicacion, matching y revision humana. |
| Conceptos y relaciones | Prototipo visual del grafo ontologico | Sustituir el modelo plano por entidades versionadas, propiedades, reglas, fuentes y decisiones de revision. |
| Exportaciones JSON/Markdown | Primer mecanismo de portabilidad | Evolucionar hacia paquetes versionados, context packs y adapters de publicacion. |
| Snapshots | Intencion de versionado | Reemplazar por releases inmutables, IDs no colisionables y metadatos de ejecucion. |

## 3. Brechas que deben resolverse primero

### Fundaciones tecnicas

- No hay repositorio Git inicializado en ONTO ni estrategia de releases.
- Los IDs de documentos y snapshots se basan en segundos; pueden colisionar y ya existe una colision de documentos en el caso local.
- La aplicacion, el dominio y la persistencia estan pensados para un proyecto local, no para cliente, dominio, data product y ejecucion (`run_id`).
- La validacion es estructural; no existe validacion de evidencia, calidad semantica, ownership ni aprobacion.
- Las pruebas actuales son puntuales y no cubren contratos futuros, integridad de persistencia ni conectores.

### Brechas de producto

- Tool 01 no cubre aun PBIP/TMDL, roles, jerarquias, anotaciones, dependencias DAX, lineage ni fuentes distintas de `model.bim`.
- Tool 02 no realiza chunking ni guarda evidencia de pagina/seccion/fragmento; tampoco produce una cola de revision ni salidas de consumo formal.
- No existen Tool 03/04 para generacion y validacion de ontologia candidata.
- No existe motor de scoring, backlog de gaps, context pack generico ni Runtime investigador.
- No existe contrato de importacion/publicacion con Fabric, Databricks u otros sistemas.

## 4. Arquitectura objetivo

La futura plataforma se divide en tres productos que comparten contratos. Durante el MVP se presentan como tres areas de una misma aplicacion web monolitica; no se desplegan como servicios separados:

1. **Ontology Readiness Assessment** descubre activos y mide madurez.
2. **Ontology Registry & Validation** transforma evidencia en una ontologia aprobada y versionada.
3. **Ontology Runtime** utiliza una release aprobada para responder o investigar con fuentes gobernadas.

Los tres comparten cuatro capacidades transversales implementadas dentro del mismo proceso:

- identidad y tenancy: `client`, `domain`, `data_product`, `run_id` y roles de revision;
- evidencia y lineage: fuente, fragmento, hash, version de parser/configuracion y confianza;
- versionado: snapshots de trabajo y releases inmutables;
- interoperabilidad: importadores, mappings y publicadores de plataformas externas.

## 5. Modelo de autoridad e interoperabilidad

El producto mantiene un modelo ontologico canonico propio. Esto evita que la capacidad de assessment, validacion o Runtime dependa de una API o preview de un proveedor.

Cada elemento canonico puede vincularse a una implementacion externa mediante estos campos conceptuales:

```text
system_of_record        # private | fabric | databricks | external
external_reference      # identificador y ruta del activo externo
sync_mode               # import | publish | controlled_bidirectional
mapping_status          # proposed | approved | rejected | stale
source_evidence         # documentos, modelos, consultas o decisiones que lo sustentan
review_status           # draft | pending_review | approved | deprecated
ontology_version        # release que lo contiene
```

Asi se soportan tres modos sin duplicar decisiones de negocio:

- **Privado**: ONTO gobierna y sirve la ontologia.
- **Nativo de plataforma**: el cliente decide que Fabric o Databricks sea el sistema de registro; ONTO conserva mapping, evidencia y ciclo de revision.
- **Federado**: distintos dominios o activos tienen sistemas de registro diferentes, con una vista canonica y reglas de sincronizacion explicitas.

El producto nunca debe copiar datos de negocio para publicar una ontologia si basta con metadata, binding o referencia autorizada.

## 6. Reordenamiento propuesto del repositorio

La migracion debe ser incremental. La estructura de destino orientativa es:

```text
streamlit_app.py           # unico punto de entrada web
src/ontology_workbench/
  assessment/              # modulos internos de ingesta, inventarios y scoring
  registry/                # modelo canonico, revision y releases
  runtime/                 # context packs, planes y gateways
  interoperability/        # adapters locales Fabric/Databricks
  shared/                  # contratos, evidencia y persistencia local
data/workspaces/           # inputs, ejecuciones, evidencia y outputs locales
tests/                     # pruebas del monolito y de sus contratos
docs/
```

El codigo actual se migrara por capacidad, no mediante una reescritura inicial:

- `bim_importer.py` se convierte en el primer adapter de assessment.
- `context_scanner.py` pasa a ser parte del pipeline de conocimiento, no la autoridad final.
- `models.py`, `service.py` y `storage.py` se sustituyen gradualmente por contratos compartidos y persistencia versionada.
- `streamlit_app.py` permanece como punto de entrada del MVP; su navegacion se organiza por producto y release sin introducir un segundo frontend o una API interna.

## 7. Decisiones que se deben tomar antes de construir

1. Seleccionar el primer dominio piloto y un conjunto de fuentes reales autorizado.
2. Definir el modelo canonico minimo y el vocabulario de estados de revision.
3. Definir el contrato de carpetas locales y el uso minimo de SQLite; un almacenamiento compartido queda fuera de esta etapa.
4. Acordar la primera plataforma externa prioritaria: Fabric, Databricks o ninguna para el piloto.
5. Definir politica de LLM: proveedor, residencia, datos permitidos, retencion y evaluacion.
6. Acordar quien puede aprobar definiciones, reglas, mappings y releases.
