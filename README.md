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
- Argos: investigador de releases con abstención explícita y batería local de evaluación de respuestas y evidencia.
- Interoperabilidad: paquetes locales de mapping revisable para Microsoft Fabric o Databricks, sin publicación externa.
- Snapshots locales para versionado simple y restauracion.

### Alcance actual del piloto Fabric

Fabric se utiliza como fuente técnica autorizada para descubrir metadata, validar bindings y ejecutar cuatro consultas agregadas read-only nombradas. La operación del piloto permanece dentro de la aplicación local: Atlas, Nexo, Argos y los mappings se ejecutan sobre artefactos locales. No se acepta SQL libre, no se leen filas de detalle desde la interfaz y no se publica ningún cambio externo.

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

## Prompts externos

Los prompts del scanner quedaron fuera del codigo para que puedan modificarse sin tocar Python.

- `prompts/tool2_business_context_extraction.md`

## Proximo foco sugerido

- Ajustar el modelo y los flujos al contenido real del Tool 01.
- Definir reglas de validacion semantica de negocio.
- Diseñar el contrato de publicacion hacia Fabric.
