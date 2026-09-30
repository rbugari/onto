# DataIA Ontology Factory (ONTO)

ONTO convierte evidencia tecnica y funcional existente en conocimiento ontologico gobernado, revisable y consumible por IA. Su foco son los dominios cuyos datos estan **distribuidos en varios sistemas y plataformas**: releva, cruza y hace aprobar ese conocimiento para **entregarlo a la plataforma del cliente** (Fabric, Databricks u otra) y que lo implemente en su propia ontologia.

**ONTO no compite con la ontologia de Fabric ni con la de Databricks.** La ruta por defecto es implementar en la plataforma del cliente; ONTO solo sostiene por su cuenta la parte que la plataforma no puede cubrir (plan B).

**Empezar por:** [Objetivo, alcance y foco](docs/OBJETIVO_ALCANCE_Y_FOCO.md). Para personas no tecnicas: [Guia paso a paso](docs/GUIA_PASO_A_PASO_NO_TECNICA.md). La direccion completa del producto esta en la [documentacion de producto](docs/README.md).

La Factory se organiza en tres productos independientes y conectables:

1. **Atlas · Preparar evidencia**: inventaria todos los sistemas del dominio y su documentacion, mapea las entidades compartidas entre sistemas y mide readiness, gaps y prioridades por caso de uso.
2. **Nexo · Validar conocimiento**: convierte evidencia en conocimiento revisado y versionado, y prepara el paquete para la plataforma destino.
3. **Argos · Investigar el negocio**: prueba la release aprobada con preguntas reales (evidencia y abstencion) y sirve como runtime de plan B para lo que la plataforma no cubre.

Fabric, Databricks, Snowflake, SQL Server, MySQL y otras plataformas pueden cumplir roles distintos. Pueden ser repositorios de datos, fuentes de evidencia, modelos semanticos o destinos de una publicacion ontologica. ONTO mantiene separado el plano de datos del plano ontologico y conserva un modelo canonico portable.

## Dos planos de interoperabilidad

- **Plano de datos:** Atlas descubre metadata y Argos consulta datos operativos mediante bindings y operaciones autorizadas. Fabric es aqui un repositorio mas, igual que Databricks, Snowflake o SQL Server.
- **Plano ontologico:** Nexo prepara la release aprobada y su mapping para implementarla en Fabric IQ Ontology, Databricks u otra herramienta externa (destino preferido). ONTO conserva la release como sistema de registro solo en el plan B.

Una misma plataforma puede participar en ambos planos, pero las capacidades, permisos y contratos no son los mismos.

## Estado de la implementacion

El codigo actual es el MVP operativo local de los tres productos. Atlas, Nexo y Argos tienen flujos ejecutables y validados para `fabric-gold-sic-risk-pilot`, `commercial-sales-demo` y `distribuidora-ventas-distribuidas` (dominio repartido en cinco sistemas); `nalub-case` funciona como caso tecnico secundario. La publicacion externa, la seguridad multiusuario y la operacion productiva siguen fuera de alcance. El alcance detallado esta en [MVP operativo](docs/00_MVP_OPERATIVO.md).

Durante esta etapa ONTO se mantiene como una unica aplicacion web local de Streamlit, con carpetas bajo `data/` y configuracion en `.env`. Assessment, Registry y Runtime se separan por contratos y navegacion, no por microservicios ni infraestructura. Ver la [decision de arquitectura MVP](docs/04_DECISION_ARQUITECTURA_MVP.md).

Al abrir la aplicacion se elige el proyecto activo y se confirma en **Contexto de trabajo**. La barra lateral muestra la ruta de tres etapas (**1. Preparar evidencia**, **2. Validar conocimiento**, **3. Investigar el negocio**), el acceso a **Administrar proyecto** y la identidad del **revisor/a de la sesion**, que se usa en todas las decisiones de revision.

## Estado actual

- Proyectos locales, snapshots, exportacion/importacion JSON y resumen Markdown.
- Conceptos, relaciones y metadata editables desde **Administrar proyecto**.
- **Atlas** en cuatro pestanas: Alcance, Fuentes, Contexto de negocio y Diagnostico.
  - Varios sistemas por proyecto, cada uno con plataforma, responsable, formato, archivo y hash SHA-256. Reimportar un sistema reemplaza solo sus objetos.
  - Carga por archivo exportado: DDL generico (`.sql`), `information_schema.columns` (CSV), `model.bim`, TMDL y PBIP ZIP. Cubre Databricks, SQL Server, PostgreSQL, Snowflake, Oracle, MariaDB y planillas.
  - Conexion directa de solo lectura a metadata de Microsoft Fabric.
  - Casos de uso con pregunta de negocio, responsable, prioridad y sistemas.
  - Scanner de contexto de negocio sobre documentos (antes "Tool 2"), con evidencia por fragmento.
  - Diagnostico reproducible: score por dimension (incluida alineacion entre sistemas), mapa de entidades compartidas, gaps por sistema/caso de uso, informe Markdown y revision humana.
- **Nexo** en cinco pestanas: revision de candidatos (lista y detalle con evidencia), modelo canonico, consolidacion, comparacion y release/interoperabilidad. Release local reconstruible con `agent_context_pack`.
- **Argos**: conversacion tipo chat sobre una release aprobada, abstencion explicita, preguntas iniciales y graficos definidos por el catalogo, y pestana de analistas con catalogo de consultas y bateria de evaluacion.
- Query catalog por release: routing, parametros, binding requerido, adapter, perfil de conexion, limites, `example_question` y `visualization`.
- Interoperabilidad: paquetes locales de mapping revisable para Microsoft Fabric o Databricks, sin publicacion externa.
- Demo distribuida sintetica: `examples/distributed_sales_demo/` y `scripts/run_distributed_demo.py` (ERP MariaDB, lakehouse Databricks, Power BI, CRM SQL Server y planillas).
- Demo comercial sintetica: `examples/commercial_sales_demo/` y `scripts/run_commercial_sales_demo.py` ejecutan Atlas, Nexo, Argos y mapping local sin datos reales.
- Caso Nalub: `scripts/run_nalub_case.py` ingesta el schema del backup y el contexto funcional, genera una release con cinco capacidades MariaDB y puede ejecutar consultas live read-only con un perfil de conexion local.
- Conexiones por proyecto: los perfiles viven en `data/connections/<project_id>/<profile_id>.env`; una release solo referencia el nombre del perfil y nunca persiste secretos.

### Pilotos y casos de validacion

El piloto `fabric-gold-sic-risk-pilot` valida una primera combinacion de ambos planos. Atlas descubre metadata del Warehouse; Nexo conserva bindings y prepara mappings; Argos ejecuta consultas read-only nombradas sobre datos operativos. Las queries y tablas del dominio SIC son especificas del piloto.

El caso `nalub-case` valida un flujo schema-first sobre MariaDB legacy. La release actual declara `order_status_summary`, `sales_summary`, `product_demand_by_year`, `customer_debt` y `product_availability`. Las consultas live usan solo templates allowlisted, parametros validados, sesion read-only y perfiles aislados por proyecto. No se acepta SQL libre.

## Estructura

- `streamlit_app.py`: punto de entrada, seleccion de proyecto, navegacion y administracion del proyecto.
- `onto_ui/`: pantallas `atlas.py`, `nexo.py`, `argos.py`, widgets compartidos (`common.py`) y etiquetas en espanol (`labels.py`).
- `src/ontology_workbench/`:
  - `models.py`, `service.py`, `storage.py`: dominio, logica y persistencia local.
  - `atlas.py`, `cross_source.py`, `external_metadata.py`, `bim_importer.py`, `semantic_model_importer.py`, `mariadb_schema.py`: assessment, alineacion entre sistemas e importadores.
  - `context_scanner.py`: extraccion de texto y scanner de contexto.
  - `nexo.py`, `nexo_curation.py`, `nexo_diff.py`: drafts, consolidacion, comparacion y releases.
  - `runtime.py`, `runtime_evaluation.py`, `query_catalog.py`, `result_views.py`: Argos, evaluacion, catalogo y presentacion de resultados.
  - `fabric_adapter.py`, `mariadb_adapter.py`, `local_data_adapter.py`, `connection_profiles.py`, `interoperability.py`: conectores y mappings.
- `tests/test_workbench_service.py`: pruebas de servicio y contratos.
- `tests/test_streamlit_ui.py`: pruebas de interfaz con `streamlit.testing.v1.AppTest` (se omiten si Streamlit no esta instalado).
- `examples/`: casos sinteticos versionables. `scripts/`: runners y demos.

## Ejecutar local

1. Crear y activar un entorno virtual.
2. Instalar dependencias.
3. Levantar la app.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Verificacion rapida

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m compileall -q streamlit_app.py onto_ui src scripts tests
```

Con el Python del entorno virtual se ejecutan tambien las pruebas de interfaz. Los tests de UI usan `ONTO_DATA_DIR` apuntando a una carpeta temporal y no tocan `data/`.

## Ejecutar las demos

Dominio distribuido en varios sistemas (foco de Atlas):

```powershell
python scripts/run_distributed_demo.py
```

Flujo completo Atlas, Nexo, Argos y mapping con datos sinteticos:

```powershell
python scripts/run_commercial_sales_demo.py
```

Ambos scripts regeneran solo los artefactos de su propio proyecto demo.

## Ejecutar la demo local

Con una release Nexo ya aprobada, la demo muestra el context pack, ejecuta una pregunta respondible, una abstencion y la bateria Argos:

```powershell
python scripts/run_onto_demo.py fabric-gold-sic-risk-pilot
```

Para consultar una pregunta propia o evitar la bateria automatica:

```powershell
python scripts/run_onto_demo.py fabric-gold-sic-risk-pilot --question "Que es gold_sic.fact_riesgo?"
python scripts/run_onto_demo.py fabric-gold-sic-risk-pilot --skip-evaluation
```

## Ejecutar procesos auxiliares

Para ejecutar solo el scanner de contexto y dejar su estado en `data/context/<project>/working/llm_scan_status.json`:

```powershell
python scripts/run_context_scan.py fabric-gold-sic-risk-pilot
```

Para generar sugerencias de consolidación de un draft Nexo ya existente:

```powershell
python scripts/run_nexo_consolidation.py fabric-gold-sic-risk-pilot <draft-id>
```

Ambos procesos escriben un archivo de estado con resultado, fecha y error controlado si no finalizan correctamente.

## Ejecutar el piloto guiado

Para repetir el ciclo desde cero con pausas de verificacion y confirmaciones humanas:

```powershell
$env:ONTO_LLM_PROVIDER="disabled"
python scripts/run_guided_pilot.py
```

El runner conserva los documentos fuente, limpia solo los artefactos operativos de
`fabric-gold-sic-risk-pilot` y espera confirmacion en cada etapa. En Nexo aplica una
regla automatica de analista: aprueba evidencia disponible con origen identificado
y confianza suficiente, y rechaza el resto dejando una decision trazable. La
publicacion de la release se ejecuta automaticamente cuando no quedan pendientes.

Si una etapa requiere correccion, se puede retomar sin repetir las anteriores:

```powershell
python scripts/run_guided_pilot.py --from-step 8
```

Para ejecutar sin limpiar datos operativos, usar `--skip-reset`.

## Persistencia local

La raiz es `data/` o la carpeta indicada en `ONTO_DATA_DIR`.

- Proyectos (incluye sistemas y casos de uso): `data/projects/*.json`
- Snapshots: `data/history/<project-id>/*.json`
- Metadata tecnica y documentos: `data/context/<project-id>/...`
- Diagnosticos Atlas: `data/workspaces/<client>/<domain>/<data-product>/runs/<run-id>/...`
- Registry: `data/registry/<project-id>/...`
- Interoperabilidad: `data/interoperability/<project-id>/<release-id>/<target>/...`
- Conexiones: `data/connections/<project-id>/<profile>.env` (secretos locales, no versionar)
- Runtime: `data/runtime/<project-id>/<release-id>/<investigation-id>/...`

## LLM para el scanner de contexto y Argos

La app no puede usar tu sesion de Copilot como backend runtime. Para el scanner con LLM necesitas configurar un proveedor propio o correr en modo heuristico local.

Variables de entorno soportadas:

```powershell
$env:ONTO_LLM_PROVIDER="disabled"      # disabled | openai | azure_openai | ollama
$env:ONTO_LLM_MODEL="gpt-4.1-mini"
$env:ONTO_LLM_API_KEY="..."
$env:ONTO_LLM_BASE_URL="https://api.openai.com/v1"
```

Tambien se aceptan variables estilo Azure ya existentes en `.env`, por ejemplo:

```powershell
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_DEPLOYMENT_ID=gpt-4.1
```

Para reutilizar un proveedor compartido sin duplicar la clave, indicar su archivo de configuracion:

```powershell
$env:ONTO_LLM_CONFIG_PATH="C:\ruta\al\proveedor-compartido\.env"
```

El archivo compartido puede declarar `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY` y, si hace falta, `LLM_BASE_URL`. Las variables locales `ONTO_LLM_*` tienen prioridad. La aplicacion solo informa proveedor/modelo y nunca muestra la clave.

Para modelos de razonamiento compatibles con Chat Completions se admite `LLM_REASONING_EFFORT` en el archivo compartido o `ONTO_LLM_REASONING_EFFORT` localmente. El valor por defecto para OpenAI es `none`, consistente con el proveedor compartido actual.

Si existe `.env` en la raiz del proyecto, la app lo carga automaticamente.

`ONTO_LLM_DATA_POLICY` controla que se puede enviar al proveedor: `approved_external` (por defecto) permite el proveedor configurado; `local_only` bloquea proveedores externos y solo admite Ollama local.

Para Azure OpenAI:

```powershell
$env:ONTO_LLM_PROVIDER="azure_openai"
$env:ONTO_AZURE_OPENAI_ENDPOINT="https://<resource>.openai.azure.com"
$env:ONTO_AZURE_OPENAI_DEPLOYMENT="<deployment>"
$env:ONTO_AZURE_OPENAI_API_VERSION="2024-10-21"
$env:ONTO_LLM_API_KEY="..."
```

Para local sin clave:

```powershell
$env:ONTO_LLM_PROVIDER="ollama"
$env:ONTO_LLM_MODEL="llama3.1:8b"
$env:ONTO_LLM_BASE_URL="http://localhost:11434/api/chat"
```

## Configuracion MariaDB Nalub

El runner live usa un perfil por proyecto con `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` y `DB_NAME`. El perfil no se copia a la release ni al contexto.

```powershell
python scripts/run_nalub_case.py --live --project-id nalub-case --connection-profile nalub-test
```

La consulta de demanda por producto acepta un año entre 2000 y 2100 y excluye pedidos cancelados. El adapter no ejecuta SQL recibido desde la pregunta.

## Configuracion Fabric

La integración Fabric es opcional y de solo lectura. Requiere dependencias ya incluidas en `requirements.txt`, el controlador ODBC 18 para SQL Server y un archivo `.env` compartido autorizado. ONTO no guarda secretos: se configura únicamente la ruta del archivo y, opcionalmente, la ruta del registro local de autenticación.

```powershell
$env:ONTO_FABRIC_CONFIG_PATH="C:\ruta\a\fabric\.env"
$env:ONTO_FABRIC_AUTH_RECORD_PATH="C:\ruta\local\fabric-auth-record.json" # opcional
```

El archivo compartido debe definir `FABRIC_AUTH_MODE=interactive_browser`, `FABRIC_WAREHOUSE_SERVER`, `FABRIC_WAREHOUSE_DATABASE`, `FABRIC_TENANT_ID`, `FABRIC_CLIENT_ID` y `FABRIC_AUTH_METHOD` (`interactive_browser` o `device_code`). Si no se indica `ONTO_FABRIC_AUTH_RECORD_PATH`, se usa `data/fabric-auth-record.json` junto al archivo compartido. Atlas limita el descubrimiento a `INFORMATION_SCHEMA`; Argos solo ejecuta consultas nombradas y vinculadas por una release aprobada.

## Prompts externos

Los prompts del scanner quedaron fuera del codigo para que puedan modificarse sin tocar Python.

- `prompts/tool2_business_context_extraction.md`

## Evolucion posterior al MVP

- Formalizar contratos separados para fuentes de datos, modelos semanticos y repositorios ontologicos externos.
- Descubrimiento remoto de metadata para Databricks (Unity Catalog) y otras plataformas; hoy se cargan por archivo exportado.
- Confirmacion humana de equivalencias entre sistemas (por ejemplo Cuenta CRM = Cliente ERP) como parte de Nexo.
- Registrar templates y adapters de ejecucion para catalogos de nuevos dominios.
- Ampliar la cobertura de consultas operativas comerciales y sus evaluaciones.
- Consolidar la politica de datos demo y separar artefactos operativos del repo.
- Definir reglas de validacion semantica de negocio y revisión de impacto.
- Diseñar y validar un adapter de publicación externo controlado.
- Curar los matches ambiguos y los gaps del flujo `documentation-first` antes de emitir releases de negocio.
- Ampliar la cobertura de evaluación y permisos del Runtime.
