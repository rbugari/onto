# DataIA Ontology Factory (ONTO)

ONTO evoluciona desde el MVP local existente hacia una plataforma de conocimiento ontologico gobernado. La direccion del producto esta definida en la [documentacion de producto](docs/README.md).

La Factory se organiza en tres productos independientes y conectables:

1. **Atlas · Ontology Readiness Assessment**: inventaria activos y mide readiness, gaps y prioridades.
2. **Nexo Â· Ontology Registry & Validation**: convierte evidencia en una ontologia validada, versionada y portable.
3. **Ontology Runtime**: usa una release aprobada para responder o investigar con evidencia y abstencion.

Fabric, Databricks y otras plataformas son fuentes, sistemas de registro opcionales o destinos de publicacion; no sustituyen el modelo canonico de ONTO.

## Estado de la implementacion

El codigo actual es un MVP local que aporta primeras capacidades de ingesta y exploracion. Corresponde principalmente al inicio del producto Assessment y no debe interpretarse como la Factory completa.

Durante esta etapa ONTO se mantiene como una unica aplicacion web local de Streamlit, con carpetas bajo `data/` y configuracion en `.env`. Assessment, Registry y Runtime se separan por contratos y navegacion, no por microservicios ni infraestructura. Ver la [decision de arquitectura MVP](docs/04_DECISION_ARQUITECTURA_MVP.md).

La entrada web es una portada de **Ontology Factory**: permite elegir el proyecto activo y abrir Atlas, Nexo, Argos o el Workbench operativo. Cada producto se visualiza como un area independiente dentro de la misma aplicacion local.

## Estado actual

- Creacion de proyectos locales.
- Alta, edicion y borrado de conceptos y relaciones.
- Edicion de datos basicos del proyecto.
- Metadata por proyecto.
- Validacion estructural basica.
- Exportacion a JSON y resumen Markdown.
- Importacion desde JSON exportado.
- Importacion de archivos model.bim sobre el proyecto activo.
- Captura local del `model.bim` original, con hash SHA-256, como evidencia de Atlas.
- Tool 2 local: carga de documentos y scanner de contexto de negocio.
- Atlas: assessment package reproducible con inventarios, evidencia por fragmentos, score basal, gaps y registro de revision humana; puede incorporar metadata Fabric de solo lectura como evidencia técnica.
- Nexo: draft de candidatos trazables, modelo canónico revisable (propiedades, relaciones, sinónimos y restricciones) y release local inmutable con `agent_context_pack`.
- Argos: investigador de releases con abstención explícita, recuperación trazable y batería local de evaluación de respuestas y evidencia; la release documentation-first del piloto Fabric pasa 6/6 casos.
- Interoperabilidad: paquetes locales de mapping revisable para Microsoft Fabric o Databricks, sin publicación externa.
- Snapshots locales para versionado simple y restauracion.

### Alcance actual del piloto Fabric

Fabric se utiliza como fuente técnica autorizada para descubrir metadata, validar bindings y ejecutar seis consultas read-only nombradas. La operación del piloto permanece dentro de la aplicación local: Atlas, Nexo, Argos y los mappings se ejecutan sobre artefactos locales. No se acepta SQL libre ni se publica ningún cambio externo; dos operaciones parametrizadas recuperan un máximo controlado de filas para una regla/SIC o un SIC específico.

## Estructura

- `streamlit_app.py`: interfaz local.
- `src/ontology_workbench/models.py`: modelos del dominio.
- `src/ontology_workbench/service.py`: logica del workbench.
- `src/ontology_workbench/storage.py`: persistencia en archivos JSON y snapshots.
- `src/ontology_workbench/exporters.py`: salidas portables.
- `src/ontology_workbench/context_scanner.py`: extraccion de texto y scanner Tool 2.
- `tests/test_workbench_service.py`: pruebas unitarias.

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
python -m unittest discover -s tests
python -m compileall src tests streamlit_app.py
```

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

- Proyectos: `data/projects/*.json`
- Snapshots: `data/history/<project-id>/*.json`
- Tool 2: `data/context/<project-id>/...`

## LLM para Tool 2

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

## Proximo foco sugerido

- Ampliar el adaptador técnico más allá de `model.bim` y el catálogo Fabric actual.
- Definir reglas de validacion semantica de negocio y revisión de impacto.
- Diseñar y validar un adapter de publicación externo controlado.
- Curar los matches ambiguos y los gaps del flujo `documentation-first` antes de emitir releases de negocio.
- Ampliar la cobertura de evaluación y permisos del Runtime.
