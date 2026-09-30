# ONTO — Plan de ajuste de repo, posicionamiento y próximos pasos

**Fecha:** 2026-08-13  
**Estado:** plan actualizado con el caso Nalub live y el catalogo multi-adapter de Argos. Las capacidades implementadas deben distinguirse del roadmap de publicacion externa y operacion productiva.
**Proyecto:** `rbugari/onto`  
**Objetivo del documento:** dejar una guía completa para que un agente de desarrollo planifique tareas, ajuste el repo, ordene la documentación y alinee el producto ONTO con el mensaje correcto de consultoría, demo y evolución técnica.

---

## 1. Contexto general

ONTO avanzó desde una idea inicial de consultoría sobre ontología para agentes hacia una base de producto concreta: una **Ontology Factory** orientada a preparar conocimiento gobernado para IA.

El repositorio ya contiene una estructura conceptual sólida con tres productos principales:

1. **Atlas — Ontology Readiness Assessment**  
   Evalúa cómo está un cliente, dominio o data product respecto a preparación ontológica para IA.

2. **Nexo — Ontology Registry & Validation**  
   Convierte la evidencia de Atlas en candidatos ontológicos, permite revisión humana y emite una release aprobada, versionada y portable.

3. **Argos — Ontology Runtime / Investigador**  
   Usa una release aprobada para responder preguntas con evidencia, límites y abstención explícita.

Además, existe una capa de **interoperabilidad** con Fabric, Databricks y otras plataformas como fuentes, destinos o sistemas de registro opcionales.

La evolución es muy positiva, pero ahora es necesario consolidar el repo y controlar el mensaje para evitar que ONTO parezca una herramienta genérica de “organizar todos los datos”.

---

## 2. Mensaje correcto del producto

### 2.1 Qué hace ONTO

ONTO toma modelos, documentación, catálogos y evidencia técnica existente, y los transforma en conocimiento ontológico gobernado para que pueda ser usado por agentes de IA con trazabilidad, límites y abstención.

### 2.2 Qué NO hace ONTO

ONTO no reemplaza la plataforma de datos del cliente, su catálogo, su gobierno, ni su herramienta de ontologías. ONTO se integra con ellos y genera paquetes portables.

### 2.3 Por qué existe ONTO

El problema no es solo tener datos. El problema es que la IA entienda qué significan, qué puede usar, qué está aprobado y cuándo debe abstenerse.

### 2.4 Frase de posicionamiento recomendada

> ONTO convierte evidencia técnica y funcional existente en conocimiento ontológico gobernado, revisable y consumible por IA.

### 2.5 Frase que se debe evitar

Evitar mensajes como:

- “ONTO organiza todos los datos de la empresa”.
- “ONTO trackea todos los datos”.
- “ONTO reemplaza el catálogo o el gobierno de datos”.
- “ONTO crea automáticamente la ontología final”.
- “ONTO inventa un nuevo estándar de ontologías”.

### 2.6 Formulación correcta

Usar expresiones como:

- “inventariamos activos relevantes”;
- “preservamos evidencia”;
- “generamos conocimiento candidato”;
- “validamos releases ontológicas”;
- “preparamos contexto gobernado para IA”;
- “publicamos o exportamos mappings hacia herramientas del cliente”.

---

## 3. Los tres productos deben quedar claros

## 3.1 Atlas — Te cuento cómo estás

**Tipo:** Assessment de readiness ontológico para IA.

**Qué hace:**

- inventaría modelos, documentación, metadatos y fuentes relevantes;
- conserva evidencia técnica y funcional;
- genera score basal o readiness score;
- detecta gaps, riesgos y ambigüedades;
- genera preguntas para negocio;
- propone prioridades y roadmap.

**Qué no hace:**

- no declara una ontología final;
- no aprueba definiciones;
- no publica nada en plataformas externas;
- no responde preguntas de negocio como agente final.

**Mensaje comercial:**

> Atlas permite saber si tus datos y documentación están preparados para soportar agentes de IA con contexto confiable.

---

## 3.2 Nexo — Te preparo la ontología validada

**Tipo:** Registry & Validation.

**Qué hace:**

- toma uno o más assessment packages de Atlas;
- genera candidatos ontológicos;
- permite revisión humana;
- conserva decisiones, evidencia y confidence score;
- administra estados de revisión;
- emite una release ontológica aprobada y reconstruible;
- genera `agent_context_pack`;
- genera mappings o paquetes de publicación hacia herramientas externas.

**Qué no hace:**

- no aprueba automáticamente inferencias de un LLM;
- no obliga a usar ONTO como sistema de registro final;
- no reemplaza herramientas como Purview, Unity Catalog, Fabric IQ Ontology, Collibra, Alation, Neo4j, RDF/OWL u otras.

**Mensaje comercial:**

> Nexo convierte evidencia dispersa en una release ontológica validada, portable y lista para IA.

---

## 3.3 Argos — Uso la release para consultar con seguridad

**Tipo:** Runtime / investigador / agente controlado.

**Qué hace:**

- carga una release aprobada de Nexo;
- responde solo dentro de la evidencia aprobada;
- se abstiene si no hay evidencia suficiente;
- puede usar consultas autorizadas y read-only;
- no acepta SQL libre;
- genera trazabilidad y evaluación.

**Qué no hace:**

- no lee documentos crudos directamente;
- no modifica sistemas fuente;
- no inventa definiciones;
- no elude permisos de plataforma.

**Mensaje comercial:**

> Argos permite consultar conocimiento gobernado con evidencia, límites y abstención explícita.

---

## 4. Dónde entran Fabric, Databricks y otras herramientas

La regla de diseño debe ser:

> La importación de evidencia pertenece a Atlas. La publicación/exportación pertenece a Nexo. El consumo operativo pertenece a Argos.

### 4.1 Atlas

Fabric, Databricks, Power BI, Qlik, Tableau, SQL, documentación, catálogos y wikis son **fuentes de evidencia**.

Ejemplos:

- leer metadata de Fabric Warehouse;
- importar `model.bim`, PBIP, TMDL o semantic model;
- leer metadatos de Unity Catalog;
- cargar documentación funcional;
- leer exports de Qlik/Tableau/Excel cuando no haya modelos semánticos formales.

### 4.2 Nexo

Fabric, Databricks, Purview, Fabric IQ Ontology, Unity Catalog, Collibra, Alation, Neo4j, RDF/OWL, JSON, Excel u otras herramientas son **destinos, sistemas de registro opcionales o formatos de publicación/mapping**.

Ejemplos:

- generar un paquete para Fabric IQ Ontology;
- generar mapping hacia Unity Catalog;
- exportar glosario a Excel;
- generar RDF/OWL opcional;
- generar JSON canónico ONTO;
- preparar package para catálogo externo.

### 4.3 Argos

Fabric, Databricks u otros sistemas son **fuentes operativas consultables**, solo mediante bindings, permisos y contratos aprobados.

Ejemplos:

- consulta Fabric read-only mediante query catalog;
- consulta Databricks SQL con allowlist;
- ejecución parametrizada, no SQL libre;
- abstención si no hay binding aprobado.

---

## 5. ONTO no inventa la pólvora

ONTO debe posicionarse como una Factory de preparación ontológica para IA, no como “la herramienta definitiva de ontologías”.

Si el cliente ya tiene herramientas, ONTO debe poder integrarse con ellas.

Herramientas posibles:

- Microsoft Purview;
- Fabric IQ Ontology;
- Fabric Data Agent;
- Unity Catalog;
- Databricks Genie / Mosaic AI / Vector Search;
- Collibra;
- Alation;
- Informatica;
- Neo4j;
- RDF/OWL stores;
- glosarios internos;
- Excel o catálogos manuales gobernados.

### Principio de interoperabilidad

> ONTO puede usar herramientas externas como fuente, destino o sistema de registro, pero conserva un modelo canónico propio para mantener portabilidad, evidencia y control de ciclo de vida.

---

## 6. Relación entre las seis tools originales y la estructura actual

Aunque el repo evolucionó hacia Atlas, Nexo y Argos, conviene mantener una tabla de trazabilidad contra las seis tools originales para conectar la propuesta de consultoría con la implementación.

| Tool original | Producto ONTO actual | Estado esperado |
| --- | --- | --- |
| Tool 01 — Semantic Model & BI Metadata Scanner | Atlas adapters | Importa metadata técnica: `model.bim`, Fabric, futuro PBIP/TMDL/API, Databricks, Qlik/Tableau cuando aplique. |
| Tool 02 — Business Context Scanner | Atlas context scanner | Lee documentación con LLM/heurística y produce contexto funcional estructurado. |
| Tool 03 — Ontology Candidate Generator | Nexo draft generator | Cruza evidencia técnica y funcional para generar candidatos revisables. |
| Tool 04 — Ontology Review & Validation Workbench | Nexo review workflow | Permite aprobar/rechazar candidatos, bindings y elementos canónicos. |
| Tool 05 — Readiness & Gap Scoring Engine | Atlas scoring + gaps | Calcula score basal, gaps, riesgos y prioridades. Evolucionar a scoring más rico. |
| Tool 06 — Agent Context Pack & Publisher | Nexo release + interoperability packages | Genera context pack, mapping y paquetes de publicación/exportación. |
| Runtime / agente | Argos | Usa releases aprobadas para responder con evidencia y abstención. |

---

## 7. Ordenamiento urgente del repositorio

El repo debe ser presentable como base de producto y no como experimento con artefactos de piloto.

### 7.1 Problema actual

Hay datos y artefactos bajo `data/` que parecen pertenecer al piloto `fabric-gold-sic-risk-pilot`, incluyendo documentación, evidencias, contextos, releases y outputs.

Esto genera riesgos:

- exposición de datos o documentación sensible;
- repo difícil de entender;
- demos mezcladas con trabajo operativo;
- historia Git contaminada con artefactos no deseados;
- contradicción con el mensaje de gobernanza y mínimo privilegio.

### 7.2 Objetivo

Separar claramente:

- código fuente;
- documentación de producto;
- documentación técnica;
- demos dummy;
- artefactos generados localmente;
- datos reales o semi-reales fuera del repo.

### 7.3 Acción recomendada sobre `.gitignore`

Agregar reglas para ignorar outputs y datos operativos:

```gitignore
# Local runtime data
data/**
!data/samples/**
!data/demo/**
!data/.gitkeep

# Local databases / state
*.db
*.sqlite
*.sqlite3
*.log
*.tmp

# Local env / secrets
.env
.env.*
!.env.example

# Python / Streamlit
.venv/
__pycache__/
.pytest_cache/
.mypy_cache/
.streamlit/
```

### 7.4 Política de datos demo

Crear un documento:

```text
docs/09_DEMO_DATA_POLICY.md
```

Debe establecer:

- no versionar datos reales de clientes;
- no versionar documentación interna sensible;
- no versionar outputs operativos bajo `data/`;
- usar `examples/` o `data/samples/` solo con datos dummy;
- anonimizar cualquier metadata real antes de compartir;
- limpiar historia Git si se detecta material sensible.

### 7.5 Limpieza de historia Git

Si ya se versionó material sensible, no alcanza con borrarlo del último commit. Evaluar:

```bash
git filter-repo
```

o BFG Repo-Cleaner.

Después de limpiar historia:

- forzar push si corresponde;
- rotar secretos si existieron;
- documentar la limpieza.

---

## 8. Estructura recomendada del repo

Propuesta objetivo incremental:

```text
onto/
  README.md
  .env.example
  .gitignore
  requirements.txt
  streamlit_app.py

  docs/
    README.md
    01_DIAGNOSTICO_Y_TRANSFORMACION.md
    02_PRD_ONTOLOGY_FACTORY.md
    03_PLAN_ALTO_NIVEL.md
    04_DECISION_ARQUITECTURA_MVP.md
    05_ATLAS_ASSESSMENT_MVP.md
    06_NEXO_REGISTRY_MVP.md
    07_ARGOS_RUNTIME_MVP.md
    08_INTEROPERABILIDAD_MVP.md
    09_DEMO_DATA_POLICY.md
    10_POSITIONING_AND_BOUNDARIES.md
    11_EXPORT_AND_INTEROPERABILITY_STRATEGY.md
    12_DEMO_END_TO_END.md
    13_PRESENTATION_SOURCE_OF_TRUTH.md

  src/ontology_workbench/
    shared/
      contracts.py
      evidence.py
      ids.py
      paths.py
    assessment/
      atlas.py
      adapters/
        bim.py
        fabric_metadata.py
        tmdl.py
        databricks_metadata.py
    registry/
      nexo.py
      review.py
      release.py
    runtime/
      argos.py
      query_catalog.py
    interoperability/
      fabric_mapping.py
      databricks_mapping.py
      exporters.py

  examples/
    commercial_sales_demo/
      README.md
      input/
        semantic_model/
        documentation/
        metadata/
      expected_output/

  prompts/
    tool2_business_context_extraction.md
    nexo_candidate_generation.md
    argos_runtime_answering.md

  scripts/
    run_context_scan.py
    run_guided_pilot.py
    run_nexo_consolidation.py
    run_onto_demo.py

  tests/
    test_workbench_service.py
    test_atlas_contracts.py
    test_nexo_release.py
    test_argos_runtime.py
    test_interoperability_packages.py
```

No es necesario hacer esta estructura completa de golpe. Migrar por capacidad, sin reescritura masiva.

---

## 9. El ciclo de presentaciones debe venir del repo

Este punto es clave.

Toda presentación, demo ejecutiva o deck comercial debe generarse o actualizarse desde contenido versionado en el repo.

### 9.1 Problema a evitar

Evitar que cada presentación invente un relato nuevo y empiece a decir cosas distintas como:

- “ONTO organiza todos tus datos”;
- “ONTO reemplaza el catálogo”;
- “ONTO genera ontologías automáticamente”;
- “ONTO es una plataforma de gobierno de datos completa”.

### 9.2 Solución

Crear un documento fuente:

```text
docs/13_PRESENTATION_SOURCE_OF_TRUTH.md
```

Debe contener:

- elevator pitch;
- problema;
- propuesta de valor;
- qué hace y qué no hace ONTO;
- descripción de Atlas, Nexo y Argos;
- arquitectura conceptual;
- flujo end-to-end;
- relación con Fabric/Databricks;
- demo story;
- límites y riesgos;
- próximos pasos.

### 9.3 Deliverables derivados

Las presentaciones deben ser derivadas del repo:

```text
deliverables/
  executive_deck/
  technical_deck/
  demo_script/
  screenshots/
```

Idealmente, cada deck debe indicar:

- commit o versión del repo;
- fuente documental utilizada;
- fecha de generación;
- estado: draft / reviewed / approved.

### 9.4 Regla

> Si una idea no está en `docs/`, no debería aparecer como promesa fuerte en una presentación.

---

## 10. Segundo ejemplo / nuevo proyecto comercial

Se necesita un segundo caso que no esté ligado a riesgo/SIC para demostrar que ONTO no es un experimento específico.

### 10.1 Caso recomendado

**Commercial Sales Demo**

Dominio:

```text
commercial / sales / customer-orders
```

Entidades posibles:

- Cliente;
- Pedido;
- Producto;
- Factura;
- Vendedor;
- Región;
- Canal;
- Campaña;
- Venta;
- Margen;
- Cliente activo.

KPIs posibles:

- Ventas netas;
- Ventas brutas;
- Descuentos;
- Devoluciones;
- Margen bruto;
- Ticket promedio;
- Clientes activos;
- Recurrencia;
- Pedidos cancelados;
- Venta por región;
- Venta por vendedor.

### 10.2 Uso de base real de cliente

Si existe una base comercial real accesible, usarla con mucho cuidado.

Opciones recomendadas:

#### Opción A — Metadata real + datos dummy

- usar nombres de tablas/columnas reales autorizados;
- no copiar datos personales ni transacciones reales;
- generar datos sintéticos;
- anonimizar nombres sensibles.

#### Opción B — Modelo sintético inspirado en el cliente

- recrear estructura similar;
- usar nombres genéricos;
- no usar datos ni documentación real;
- ideal para demo pública o interna amplia.

Para presentaciones externas, preferir opción B.

### 10.3 Documentación mínima a crear

Aunque el cliente tenga poca documentación, crear una documentación mínima dummy para probar el flujo:

```text
examples/commercial_sales_demo/input/documentation/
  01_glosario_comercial.md
  02_definicion_kpis_ventas.md
  03_proceso_pedido_facturacion.md
  04_diccionario_modelo_comercial.md
  05_preguntas_negocio_frecuentes.md
```

### 10.4 Valor demo

Este caso permite mostrar:

- que Atlas funciona aunque la documentación sea pobre;
- que ONTO detecta gaps;
- que Nexo exige revisión humana;
- que Argos responde dentro de una release aprobada;
- que el sistema puede abstenerse ante preguntas fuera de alcance.

---

## 11. Estrategia de exportación e interoperabilidad

Crear un documento:

```text
docs/11_EXPORT_AND_INTEROPERABILITY_STRATEGY.md
```

### 11.1 Principio

ONTO debe ser portable. La ontología canónica puede quedarse en ONTO, exportarse o mapearse a la herramienta que el cliente prefiera.

### 11.2 Tipos de salida

#### Salida canónica ONTO

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

#### Salida ejecutiva / consultoría

- Markdown summary;
- Excel review workbook;
- PowerPoint ejecutivo;
- dashboard de readiness;
- backlog de gaps.

#### Salida técnica

- JSON canónico;
- JSON-LD opcional;
- RDF/OWL opcional;
- CSV/Excel de glosario;
- mapping Fabric;
- mapping Databricks;
- mapping Purview/Collibra/Alation futuro.

### 11.3 Import / Map / Publish

Separar claramente:

| Operación | Producto | Descripción |
| --- | --- | --- |
| Importar | Atlas | Trae evidencia y metadata desde plataformas. |
| Mapear | Nexo | Vincula elementos canónicos aprobados con objetos externos. |
| Publicar | Nexo | Genera o actualiza representación externa, solo desde una release aprobada. |
| Consultar | Argos | Usa bindings aprobados para responder o consultar datos. |

### 11.4 Fabric

Posibles destinos:

- Fabric IQ Ontology;
- Fabric Data Agent context;
- Lakehouse Knowledge Layer fallback;
- Power BI semantic model annotations;
- Purview glossary o catálogo, si aplica.

### 11.5 Databricks

Posibles destinos:

- Unity Catalog tags/comments;
- Lakehouse monitoring / metadata mapping;
- Databricks SQL query catalog;
- Mosaic AI / Genie context pack;
- Vector Search para documentación aprobada;
- JSON package portable.

### 11.6 Fallback genérico

Si el cliente no quiere Fabric/Databricks como destino:

- exportar JSON canónico;
- exportar Excel revisable;
- exportar RDF/OWL si lo necesita;
- exportar paquete documental para su herramienta interna.

---

## 12. Query catalog de Argos debe ser configurable

### 12.1 Problema actual

El runtime Fabric actual está demasiado ligado al caso `gold_sic.fact_riesgo` y tiene queries hardcodeadas.

Eso está bien para el piloto, pero debe generalizarse.

### 12.2 Objetivo

Mover el query catalog desde código hardcodeado hacia configuración de release o data product.

Ejemplo:

```json
{
  "query_catalog": [
    {
      "query_name": "sales_by_customer",
      "description": "Ventas por cliente",
      "binding_required": "commercial.fact_sales",
      "allowed_parameters": ["customer_id"],
      "operation": "SELECT",
      "template_id": "fabric.sales_by_customer.v1",
      "max_rows": 100
    }
  ]
}
```

### 12.3 Regla

Argos nunca debe aceptar SQL libre. Solo debe ejecutar operaciones nombradas, parametrizadas y autorizadas por una release.

---

## 13. Roadmap de tareas para el agente

## Fase 1 — Control del mensaje y documentación base

### Tarea 1.1 — Crear documento de posicionamiento

Crear:

```text
docs/10_POSITIONING_AND_BOUNDARIES.md
```

Debe incluir:

- qué hace ONTO;
- qué no hace;
- frase de posicionamiento;
- productos Atlas/Nexo/Argos;
- límites;
- relación con herramientas externas;
- anti-promesas.

### Tarea 1.2 — Crear source of truth para presentaciones

Crear:

```text
docs/13_PRESENTATION_SOURCE_OF_TRUTH.md
```

Debe incluir narrativa oficial para decks.

### Tarea 1.3 — Ajustar README principal

Actualizar `README.md` para que:

- abra con posicionamiento correcto;
- explique Atlas/Nexo/Argos en 30 segundos;
- aclare estado MVP;
- enlace a docs principales;
- evite promesas excesivas.

---

## Fase 2 — Limpieza de repo

### Tarea 2.1 — Revisar `data/`

Identificar artefactos versionados bajo `data/`.

Clasificar:

- conservar como demo dummy;
- mover fuera del repo;
- eliminar;
- anonimizar.

### Tarea 2.2 — Actualizar `.gitignore`

Aplicar reglas para ignorar datos operativos.

### Tarea 2.3 — Crear política de demo data

Crear:

```text
docs/09_DEMO_DATA_POLICY.md
```

### Tarea 2.4 — Evaluar limpieza de historia

Si hay información sensible, preparar instrucciones para `git filter-repo` o BFG.

---

## Fase 3 — Demo comercial limpia

### Tarea 3.1 — Crear estructura demo

Crear:

```text
examples/commercial_sales_demo/
```

### Tarea 3.2 — Crear documentación dummy

Crear los cinco documentos mínimos:

```text
01_glosario_comercial.md
02_definicion_kpis_ventas.md
03_proceso_pedido_facturacion.md
04_diccionario_modelo_comercial.md
05_preguntas_negocio_frecuentes.md
```

### Tarea 3.3 — Crear metadata técnica dummy

Crear uno de estos:

- `model.bim` sintético;
- TMDL sintético;
- DDL SQL;
- JSON de metadata Fabric simulada.

### Tarea 3.4 — Crear script de demo end-to-end

Crear o ajustar:

```text
scripts/run_commercial_sales_demo.py
```

Debe ejecutar:

1. crear proyecto;
2. cargar metadata;
3. cargar documentación;
4. correr scanner;
5. crear Atlas assessment;
6. crear Nexo draft;
7. aplicar revisión demo controlada;
8. emitir release;
9. ejecutar preguntas Argos;
10. producir outputs.

---

## Fase 4 — Interoperabilidad y exportación

### Tarea 4.1 — Crear estrategia documentada

Crear:

```text
docs/11_EXPORT_AND_INTEROPERABILITY_STRATEGY.md
```

### Tarea 4.2 — Separar import/map/publish/query

Asegurar que la documentación y el código usen esta separación:

- import: Atlas;
- map/publish: Nexo;
- query/runtime: Argos.

### Tarea 4.3 — Definir formato de publication package

Revisar y documentar:

```text
publication_manifest.json
mapping.json
deployment_manifest.json
rollback_manifest.json
```

### Tarea 4.4 — Preparar export genérico

Agregar o documentar export a:

- JSON canónico;
- Excel/glosario;
- Markdown summary;
- RDF/OWL opcional futuro.

---

## Fase 5 — Generalización técnica

### Tarea 5.1 — Tool 01 ampliada

Priorizar:

- PBIP;
- TMDL;
- API Fabric semantic model;
- roles/RLS;
- jerarquías;
- anotaciones;
- descripciones;
- dependencias DAX.

### Tarea 5.2 — Query catalog configurable

Extraer queries hardcodeadas de `fabric_adapter.py` y moverlas a:

- release package;
- config por data product;
- query catalog versionado.

### Tarea 5.3 — Refactor incremental

No reescribir todo. Migrar por capacidad hacia módulos:

```text
shared/
assessment/
registry/
runtime/
interoperability/
```

---

## 14. Criterios de aceptación

### 14.1 Posicionamiento

- El README y los decks no prometen “organizar todos los datos”.
- Atlas/Nexo/Argos están explicados de forma consistente.
- Queda claro que ONTO prepara conocimiento gobernado para IA.
- Queda claro que ONTO puede convivir con herramientas externas.

### 14.2 Repo

- No hay datos reales o semi-reales versionados fuera de `examples/` o `data/samples/`.
- `.gitignore` bloquea outputs locales.
- Existe política de demo data.
- La demo principal es reproducible.

### 14.3 Producto

- Atlas produce un assessment package reproducible.
- Nexo produce una release aprobada y reconstruible.
- Argos responde o se abstiene con evidencia.
- Los mappings externos están separados de la ontología canónica.

### 14.4 Demo

- Existe un segundo ejemplo comercial no ligado a riesgo/SIC.
- La demo muestra documentación pobre/parcial y gaps.
- La demo produce preguntas de negocio.
- La demo termina con un context pack y consultas Argos.

---

## 15. Prioridad recomendada inmediata

Orden sugerido:

1. Crear `docs/10_POSITIONING_AND_BOUNDARIES.md`.
2. Actualizar README principal.
3. Crear `docs/09_DEMO_DATA_POLICY.md`.
4. Limpiar `.gitignore` y revisar `data/`.
5. Crear `docs/13_PRESENTATION_SOURCE_OF_TRUTH.md`.
6. Crear demo `examples/commercial_sales_demo/`.
7. Documentar `docs/11_EXPORT_AND_INTEROPERABILITY_STRATEGY.md`.
8. Generalizar query catalog de Argos.
9. Ampliar Tool 01 a PBIP/TMDL/API Fabric.

---

## 16. Instrucción final para el agente

El agente debe trabajar con una regla central:

> El repositorio es la fuente de verdad del producto. Las presentaciones, demos, mensajes comerciales y tareas técnicas deben derivar de los documentos versionados del repo.

Antes de agregar funcionalidades nuevas, el agente debe asegurar que:

- el mensaje del producto esté controlado;
- el repo esté limpio;
- las demos no usen datos sensibles;
- Atlas, Nexo y Argos estén claramente diferenciados;
- Fabric/Databricks estén modelados como adapters, no como núcleo obligatorio;
- ONTO sea portable y no pretenda reemplazar herramientas existentes del cliente.

