"""Presentation translations; project data and stored artifacts keep their original language."""
from __future__ import annotations

from collections.abc import Mapping

import streamlit as st

LANGUAGE_KEY = "ui-language"
LANGUAGES = {"es": "Español", "en": "English"}
EN = {
    "Proyecto": "Project",
    "Contexto de trabajo": "Workspace context",
    "Selecciona un proyecto para trabajar con sus datos, contexto y decisiones.": "Select a project to work with its data, context and decisions.",
    "Proyecto validado. Listo para trabajar.": "Project validated. Ready to work.",
    "Ver validación del proyecto": "View project validation",
    "Abrir proyecto": "Open project",
    "Crear proyecto": "Create project",
    "Importar proyecto": "Import project",
    "Nombre": "Name",
    "Descripcion": "Description",
    "Ruta de trabajo": "Workflow",
    "Administrar proyecto": "Manage project",
    "Producto": "Product",
    "1. Atlas · Diagnóstico": "1. Atlas · Assessment",
    "2. Nexo · Validar conocimiento": "2. Nexo · Validate knowledge",
    "3. Argos · Investigar el negocio": "3. Argos · Investigate the business",
    "Revisor/a de esta sesión": "Session reviewer",
    "Rol": "Role",
    "Responsable de negocio": "Business owner",
    "Conceptos": "Concepts", "Relaciones": "Relationships", "Errores": "Errors", "Warnings": "Warnings",
    "Exportacion": "Export", "Descargar JSON": "Download JSON", "Descargar resumen Markdown": "Download Markdown summary",
    "Snapshots locales": "Local snapshots", "Historial disponible": "Available history", "Restaurar snapshot": "Restore snapshot",
    "Volver a productos": "Back to products", "No hay proyectos todavia. Crea uno para empezar.": "No projects yet. Create one to get started.",
    "Archivo JSON exportado": "Exported JSON file", "Preservar id si esta libre": "Keep the ID if available",
    "El proyecto no puede abrirse todavía porque tiene errores estructurales.": "The project cannot be opened yet because it has structural errors.",
    "Validacion estructural": "Structural validation", "Nota del snapshot": "Snapshot note", "Crear snapshot": "Create snapshot",
    "Todavia no hay snapshots para este proyecto.": "No snapshots for this project yet.", "Snapshot restaurado": "Snapshot restored",
    "Snapshot generado": "Snapshot created", "Metadata del proyecto": "Project metadata", "Conexiones del proyecto": "Project connections",
    "Cada perfil queda aislado en data/connections/<proyecto>. La password no se guarda en el JSON del proyecto.": "Each profile is isolated in data/connections/<project>. The password is not stored in the project JSON.",
    "Editar proyecto": "Edit project", "Importar modelo semantico": "Import semantic model",
    "Carga un model.bim, un archivo TMDL o un paquete PBIP .zip para poblar tablas, columnas, medidas y relaciones. El archivo original queda guardado localmente con hash para Atlas.": "Upload a model.bim, TMDL file or PBIP .zip package to populate tables, columns, measures and relationships. The original file is stored locally with its hash for Atlas.",
    "Archivo de modelo semantico": "Semantic model file", "Limpiar conceptos y relaciones actuales antes de importar": "Clear current concepts and relationships before importing",
    "Nota para snapshot previo": "Pre-import snapshot note", "Todavia no hay conceptos cargados.": "No concepts loaded yet.",
    "### Agregar concepto": "### Add concept", "Nombre del concepto": "Concept name", "Definicion": "Definition", "Estado": "Status",
    "Tags separados por coma": "Comma-separated tags", "Guardar concepto": "Save concept", "Todavia no hay relaciones cargadas.": "No relationships loaded yet.",
    "Necesitas al menos dos conceptos para definir relaciones.": "At least two concepts are required to define relationships.",
    "### Agregar relacion": "### Add relationship", "Origen": "Source", "Destino": "Target", "Tipo de relacion": "Relationship type",
    "Guardar relacion": "Save relationship", "Crea un proyecto desde la barra lateral para empezar.": "Create a project in the sidebar to get started.",
    "Importar JSON": "Import JSON", "No se detectaron observaciones estructurales.": "No structural issues found.",
    "Pares clave=valor, uno por linea": "Key=value pairs, one per line", "Guardar metadata": "Save metadata", "Nombre del perfil": "Profile name",
    "Puerto": "Port", "Usuario": "User", "Base de datos": "Database", "Guardar perfil MariaDB": "Save MariaDB profile",
    "Comprobar conexion": "Check connection", "Nombre del proyecto": "Project name", "Descripcion del proyecto": "Project description",
    "Guardar datos del proyecto": "Save project details", "Editar o borrar concepto": "Edit or delete concept", "Concepto": "Concept",
    "Borrar concepto": "Delete concept", "Editar o borrar relacion": "Edit or delete relationship", "Relacion": "Relationship",
    "Borrar relacion": "Delete relationship", "Proyecto importado": "Project imported", "Metadata actualizada": "Metadata updated",
    "Concepto guardado": "Concept saved", "Guardar cambios": "Save changes", "Concepto eliminado": "Concept deleted",
    "Relacion guardada": "Relationship saved", "Guardar cambios de relacion": "Save relationship changes", "Relacion eliminada": "Relationship deleted",
    "Perfil": "Profile", "Proyecto actualizado": "Project updated", "Concepto actualizado": "Concept updated", "Relacion actualizada": "Relationship updated",
    "nombre": "name", "estado": "status", "definicion": "definition", "origen": "source", "tipo": "type", "destino": "target", "descripcion": "description",
    "1. Alcance": "1. Scope", "2. Fuentes": "2. Sources", "3. Contexto de negocio": "3. Business context", "4. Diagnóstico": "4. Assessment",
    "Alcance": "Scope", "Fuentes": "Sources", "Contexto": "Context", "Diagnóstico": "Assessment", "Revisión": "Review",
    "Definí cliente, dominio y al menos un caso de uso en la pestaña **Alcance**.": "Set the client, domain and at least one use case in **Scope**.",
    "Registrá todos los sistemas del dominio y cargá su metadata en **Fuentes**.": "Register all domain systems and upload their metadata in **Sources**.",
    "Subí glosarios, KPIs o procesos y analizalos en **Contexto de negocio**.": "Upload glossaries, KPIs or processes and analyze them in **Business context**.",
    "Generá el diagnóstico en la pestaña **Diagnóstico**.": "Generate the assessment in **Assessment**.",
    "Revisá brechas y registrá la decisión en **Diagnóstico**.": "Review gaps and record the decision in **Assessment**.",
    "Universo evaluable": "Assessable inventory", "Cobertura explicativa": "Explanatory coverage", "Comparación": "Comparison", "Brechas": "Gaps",
    "Mapa entre sistemas": "Cross-system map", "Sistemas": "Systems", "Informe": "Report", "Entidades": "Entities", "Propiedades": "Properties",
    "Agregado": "Added", "Incluido": "Included", "Retirado": "Removed", "Excluido": "Excluded", "Análisis completado": "Analysis completed",
    "Clasificación cambió": "Classification changed", "Aspectos cambiaron": "Aspects changed", "Evidencia cambió": "Evidence changed",
    "Sin cambios": "Unchanged", "Explicado": "Explained", "Parcial": "Partial", "Sin explicación": "Unexplained", "Contradictorio": "Contradictory",
    "Fallo de evaluación": "Evaluation failed", "Sin evaluar": "Not evaluated", "No inventariado": "Not inventoried", "Abierto": "Open",
    "Fuera de alcance, no resuelto": "Out of scope, not resolved", "Revisar cierre": "Review closure", "Completar análisis": "Complete analysis",
    "Reintentar análisis": "Retry analysis", "Solicitar documentación": "Request documentation", "Resolver contradicción": "Resolve contradiction",
    "Atlas · Diagnóstico de preparación": "Atlas · Readiness assessment",
    "Reúne la metadata de todos los sistemas del dominio y la documentación de negocio para saber qué está listo, qué falta, cómo se conectan los sistemas y qué podrá implementar la plataforma destino.": "Brings together metadata from all domain systems and business documentation to assess readiness, gaps, system connections and what the target platform can implement.",
    "Qué se evalúa": "Assessment scope", "Casos de uso": "Use cases",
    "Cada caso de uso indica qué pregunta de negocio se quiere responder y qué sistemas necesita. Atlas los usa para priorizar las brechas.": "Each use case identifies the business question and the systems it needs. Atlas uses them to prioritize gaps.",
    "Sistemas en alcance": "Systems in scope", "Inventariados": "Inventoried", "Tablas": "Tables", "Columnas": "Columns",
    "Resultado del análisis": "Analysis results", "Generar diagnóstico": "Generate assessment", "Puntaje basal": "Baseline score", "Lectura": "Interpretation",
    "Sistemas inventariados": "Inventoried systems", "Comparación de assessments": "Assessment comparison", "Assessment inicial": "Initial assessment",
    "Sólo cambios": "Changes only", "Resultados de pedidos anteriores": "Previous request outcomes", "Descargar comparación": "Download comparison",
    "Análisis completo": "Analysis complete", "Análisis con fallos": "Analysis with failures", "Bloqueado por política": "Blocked by policy",
    "Proveedor no habilitado": "Provider disabled", "Sin universo evaluable": "No assessable inventory", "Sin evidencia documental": "No documentary evidence",
    "Descargar matriz": "Download matrix", "Grupo de cobertura": "Coverage group", "Elemento de cobertura": "Coverage element",
    "Pedidos de información": "Information requests", "Descargar pedidos": "Download requests", "Pedido para revisar": "Request to review",
    "Grupo de elementos": "Element group", "Elemento para ajustar alcance": "Element for scope adjustment", "Severidad": "Severity", "Categoría": "Category",
    "Entidades detectadas": "Detected entities", "En más de un sistema": "In multiple systems", "Con clave común": "With a common key",
    "**Sistemas técnicos**": "**Technical systems**", "Diagnóstico revisado. Podés continuar en Nexo para validar el conocimiento y prepararlo para la plataforma.": "Assessment reviewed. Continue in Nexo to validate knowledge and prepare it for the platform.",
    "Cliente": "Client", "Dominio": "Domain", "Producto de datos": "Data product", "Responsable del dominio": "Domain owner", "Guardar alcance": "Save scope",
    "Todavía no hay casos de uso.": "No use cases yet.", "Agregar caso de uso": "Add use case",
    "Registrá cada sistema que participa del dominio (ERP, lakehouse, CRM, modelos de BI, planillas). No hace falta que estén en la misma plataforma.": "Register each system in the domain (ERP, lakehouse, CRM, BI models, spreadsheets). They do not need to be on the same platform.",
    "**Agregar sistema**": "**Add system**", "**Cargar metadata de un sistema**": "**Upload system metadata**",
    "Conexión directa a Microsoft Fabric (solo lectura)": "Direct Microsoft Fabric connection (read-only)",
    "Usa la identidad Entra configurada en el entorno. Lee solo metadata (INFORMATION_SCHEMA); no lee filas ni publica cambios.": "Uses the Entra identity configured in the environment. Reads metadata only (INFORMATION_SCHEMA); does not read rows or publish changes.",
    "Schema exacto (opcional)": "Exact schema (optional)", "Filtrar tablas por nombre (opcional)": "Filter tables by name (optional)",
    "Comprobar conexión": "Check connection", "Leer metadata": "Read metadata", "Editar o quitar un sistema": "Edit or remove a system",
    "Sistema": "System", "Quitar sistema": "Remove system", "Ver objetos inventariados": "View inventoried objects", "**Subir documentos**": "**Upload documents**",
    "Tipo": "Type", "Glosarios, KPIs, procesos, diccionarios…": "Glossaries, KPIs, processes, dictionaries…",
    "El análisis anterior quedó invalidado. Volvé a analizar los documentos.": "The previous analysis was invalidated. Analyze the documents again.",
    "Configuración del motor LLM (técnico)": "LLM engine settings (technical)",
    "Sin proveedor configurado se usan reglas locales. Solo se envía contenido autorizado.": "Local rules are used when no provider is configured. Only authorized content is sent.",
    "Ver": "View", "Contraste semántico": "Semantic assessment", "Límite de llamadas": "Call budget", "Evaluar cobertura con LLM": "Evaluate coverage with LLM",
    "Todavía no hay diagnósticos para este proyecto.": "No assessments for this project yet.",
    "Hubo cambios en el proyecto después del último diagnóstico. Conviene generarlo de nuevo.": "The project changed after the latest assessment. Generate a new one.",
    "Vista": "View", "Se necesitan dos diagnósticos para comparar.": "Two assessments are required for comparison.",
    "Cambió el alcance o sus criterios. Los porcentajes tienen bases distintas; no se calcula una diferencia de avance.": "The scope or its criteria changed. Percentages use different bases; no progress difference is calculated.",
    "Mismo alcance y criterios: porcentajes comparables. Completar un análisis no equivale a resolver una falta documental.": "Same scope and criteria: comparable percentages. Completing an analysis is not the same as resolving a documentation gap.",
    "Sin cambios en clasificaciones, aspectos o evidencia citada.": "No changes in classifications, aspects or cited evidence.",
    "El assessment inicial no conserva pedidos.": "The initial assessment has no stored requests.",
    "Este diagnóstico es anterior a la matriz explicativa. Generá uno nuevo.": "This assessment predates the explanatory matrix. Generate a new one.",
    "Propuestas del LLM pendientes de revisión humana; no equivalen a aprobación en Nexo.": "LLM proposals await human review; they do not mean approval in Nexo.",
    "Sistema de cobertura": "Coverage system", "Caso de uso de cobertura": "Coverage use case", "Estados de cobertura": "Coverage states", "Aspectos faltantes": "Missing aspects",
    "Sin pedidos abiertos para esta selección.": "No open requests for this selection.",
    "Este diagnóstico es anterior al universo evaluable. Generá uno nuevo.": "This assessment predates the assessable inventory. Generate a new one.",
    "Grupo sin elementos: no evaluable.": "Empty group: not assessable.",
    "Este universo difiere del proyecto actual. Seleccioná el diagnóstico actualizado o generá uno nuevo para ajustar el alcance.": "This inventory differs from the current project. Select the latest assessment or generate a new one to adjust scope.",
    "Incluir en el universo": "Include in inventory", "Motivo del ajuste (obligatorio al excluir)": "Reason for adjustment (required for exclusion)",
    "Guardar alcance y generar diagnóstico": "Save scope and generate assessment",
    "No se detectaron brechas con las reglas basales. Igual hace falta revisión funcional.": "No gaps detected by baseline rules. Business review is still required.",
    "Este diagnóstico se generó antes del mapa entre sistemas. Generá uno nuevo.": "This assessment predates the cross-system map. Generate a new one.",
    "Se necesitan al menos dos sistemas inventariados para comparar entidades entre ellos.": "At least two inventoried systems are required to compare their entities.",
    "Ninguna entidad aparece en más de un sistema con un nombre reconocible.": "No entity appears in multiple systems with a recognizable name.",
    "Plataforma": "Platform", "Responsable": "Owner", "Formato": "Format", "Integridad": "Integrity", "**Documentos**": "**Documents**",
    "**Revisión del diagnóstico**": "**Assessment review**", "Registra la decisión humana sobre este diagnóstico. No aprueba una ontología.": "Records the human decision on this assessment. Does not approve an ontology.",
    "Tip: registrá primero los sistemas en **Fuentes** para poder vincularlos.": "Register systems in **Sources** first to link them.",
    "Pregunta de negocio": "Business question", "Prioridad": "Priority", "Sistemas que necesita": "Required systems", "Quitar": "Remove",
    "Caso de uso": "Use case", "Quitar caso de uso": "Remove use case", "Descripción (opcional)": "Description (optional)", "Agregar sistema": "Add system",
    "Primero agregá un sistema.": "Add a system first.", "Archivo de metadata": "Metadata file", "Incorporar como sistema Fabric": "Add as a Fabric system",
    "Descripción": "Description", "Tabla": "Table", "Subir": "Upload", "Todavía no hay documentos cargados.": "No documents uploaded yet.",
    "Analizar contexto de negocio": "Analyze business context", "Proveedor no habilitado o bloqueado por la política de datos. No habrá fallback heurístico.": "Provider disabled or blocked by data policy. No heuristic fallback will be used.",
    "El contraste no se completó. Los pendientes y fallos no son evidencia de ausencia de explicación.": "The assessment did not complete. Pending items and failures are not evidence of missing explanations.",
    "Elementos": "Elements", "% del alcance": "% of scope", "Elemento": "Element", "Método": "Method", "Motivo": "Reason", "Acción": "Action",
    "Responsable propuesto": "Proposed owner", "Pedido": "Request", "Criterio de cierre": "Closure criterion", "En alcance": "In scope",
    "Casos de uso (por sistema)": "Use cases (by system)", "Aspectos a explicar": "Required aspects", "ID estable": "Stable ID", "Hallazgo": "Finding",
    "Acción sugerida": "Suggested action", "Decisión": "Decision", "Revisor/a": "Reviewer", "Nota": "Note", "Guardar revisión": "Save review",
    "Acceso": "Access", "Archivo": "File", "Inventariado": "Inventoried",
    "Volver a cargar reemplaza los objetos de este sistema; los demás no cambian.": "Re-uploading replaces this system's objects; other systems are unchanged.",
    "Inventariar sistema": "Inventory system", "Hay documentos heredados con IDs duplicados; la evidencia puede no ser trazable.": "Legacy documents have duplicate IDs; evidence may not be traceable.",
    "Reparar IDs y volver a extraer": "Repair IDs and re-extract", "Término": "Term", "Definición": "Definition", "Regla": "Rule",
    "Objeto técnico": "Technical object", "Pregunta": "Question", "Generando diagnóstico…": "Generating assessment…", "Grupo": "Group", "Cambio": "Change",
    "Inicial": "Initial", "Final": "Final", "Evidencias nuevas": "New evidence", "Faltantes finales": "Final missing aspects", "Resultado": "Outcome",
    "Pedidos actuales": "Current requests", "Procesamiento del contraste": "Assessment processing", "Indicá un motivo para excluir el elemento.": "Enter a reason to exclude the element.",
    "Entidad": "Entity", "Clave común": "Common key", "Columnas clave": "Key columns", "Otras claves compartidas": "Other shared keys",
    "Caracteres": "Characters", "Subido": "Uploaded", "Contrastando universo y evidencia…": "Comparing inventory and evidence…", "Dimensión": "Dimension",
    "Cobertura": "Coverage", "Evaluados": "Evaluated", "Fallos": "Failures", "Analizando documentos…": "Analyzing documents…", "Descargar informe (Markdown)": "Download report (Markdown)",
    "Alta": "High", "Media": "Medium", "Baja": "Low", "Entre sistemas": "Cross-system", "Negocio": "Business", "Gobierno": "Governance",
    "Metadata técnica": "Technical metadata", "Contexto de negocio": "Business context", "Vínculo técnico-negocio": "Technical-business linkage",
    "Gobierno y trazabilidad": "Governance and traceability", "Alineación entre sistemas": "Cross-system alignment", "Base sólida": "Strong foundation",
    "Base parcial": "Partial foundation", "Base inicial": "Early foundation", "Pendiente de revisión": "Pending review", "Revisado": "Reviewed",
    "Requiere seguimiento": "Needs follow-up", "Todos": "All", "Pendiente": "Pending", "Aprobado": "Approved", "Rechazado": "Rejected",
    "Aceptado como plan de revisión": "Accepted as a review plan", "Sin metadata": "No metadata", "Archivo exportado": "Exported file",
    "Conexión directa (solo lectura)": "Direct connection (read-only)", "Documentación funcional": "Business documentation", "Documentación técnica": "Technical documentation",
    "Definiciones de KPI": "KPI definitions", "Diccionario de datos": "Data dictionary", "Procesos": "Processes", "Arquitectura": "Architecture", "Exportaciones de BI": "BI exports", "Otros": "Other",
    "Exportá `system.information_schema.columns` (o `<catálogo>.information_schema.columns`) a CSV, o el resultado de `SHOW CREATE TABLE` a un archivo .sql.": "Export `system.information_schema.columns` (or `<catalog>.information_schema.columns`) to CSV, or the output of `SHOW CREATE TABLE` to a .sql file.",
    "Exportá la estructura con `mysqldump --no-data` (.sql). Las filas INSERT se ignoran.": "Export the schema with `mysqldump --no-data` (.sql). INSERT rows are ignored.",
    "Generate Scripts > Schema only (.sql), o INFORMATION_SCHEMA.COLUMNS exportado a CSV.": "Generate Scripts > Schema only (.sql), or INFORMATION_SCHEMA.COLUMNS exported to CSV.",
    "`pg_dump --schema-only` (.sql), o information_schema.columns exportado a CSV.": "`pg_dump --schema-only` (.sql), or information_schema.columns exported to CSV.",
    "`GET_DDL` (.sql), o INFORMATION_SCHEMA.COLUMNS exportado a CSV.": "`GET_DDL` (.sql), or INFORMATION_SCHEMA.COLUMNS exported to CSV.",
    "DDL exportado (.sql), o ALL_TAB_COLUMNS a CSV con table_name, column_name y data_type.": "Exported DDL (.sql), or ALL_TAB_COLUMNS as CSV with table_name, column_name and data_type.",
    "model.bim, archivo TMDL o paquete PBIP comprimido (.zip).": "model.bim, TMDL file or compressed PBIP package (.zip).",
    "Usá la conexión directa (más abajo) o exportá INFORMATION_SCHEMA.COLUMNS a CSV.": "Use the direct connection below or export INFORMATION_SCHEMA.COLUMNS to CSV.",
    "Describí la estructura de las planillas en un CSV con table_name, column_name y data_type.": "Describe spreadsheet structure in a CSV with table_name, column_name and data_type.",
    "DDL (.sql) o CSV con columnas table_name, column_name y data_type.": "DDL (.sql) or CSV with table_name, column_name and data_type columns.",
    "Técnica primero: la metadata define el universo": "Technical first: metadata defines the inventory",
    "Documentación primero: el negocio define el alcance": "Documentation first: business defines the scope", "Híbrida: combina documentación y metadata": "Hybrid: combines documentation and metadata",
    "Activo técnico": "Technical asset", "Propiedad": "Property", "Relación": "Relationship", "Sinónimo": "Synonym", "Restricción": "Constraint", "Vínculo con fuente": "Source binding",
    "A · Todo en la plataforma": "A · Entirely on the platform", "B · Mixta (plataforma + ONTO)": "B · Mixed (platform + ONTO)", "C · Plan B en ONTO": "C · ONTO fallback",
    "Nexo · Validar conocimiento": "Nexo · Validate knowledge",
    "Convierte los hallazgos de Atlas en conocimiento aprobado y lo prepara para implementarlo en la ontología de Fabric, Databricks u otra plataforma del cliente. ONTO no la reemplaza: solo cubre lo que la plataforma no pueda (plan B).": "Turns Atlas findings into approved knowledge and prepares it for the ontology on Fabric, Databricks or another client platform. ONTO complements the platform, covering only what it cannot (fallback).",
    "Draft en revisión": "Draft under review", "Candidatos": "Candidates", "Pendientes": "Pending", "Aprobados": "Approved", "Rechazados": "Rejected",
    "Modelo canónico": "Canonical model", "Buscar": "Search", "Nota (opcional)": "Note (optional)",
    "Propiedades, relaciones, sinónimos, restricciones y vínculos con las fuentes. Cada elemento requiere una decisión humana antes de entrar en la release.": "Properties, relationships, synonyms, constraints and source bindings. Each element requires a human decision before inclusion in the release.",
    "Proponer vínculos con fuentes (coincidencias únicas)": "Propose source bindings (unique matches)",
    "Detecta duplicados o casi duplicados. No fusiona ni aprueba nada por sí solo.": "Detects duplicates or near-duplicates. Does not merge or approve anything automatically.",
    "Buscar duplicados": "Find duplicates", "Aceptar como plan": "Accept as a plan", "Descartar": "Dismiss",
    "Compara por tipo y nombre normalizado. No modifica candidatos ni releases.": "Compares by type and normalized name. Does not modify candidates or releases.",
    "Ruta recomendada": "Recommended route", "Implementables en la plataforma": "Platform-ready", "Falta completar": "Needs completion", "Fuera de alcance": "Out of scope",
    "Generá primero un diagnóstico en Atlas para crear un draft.": "Generate an Atlas assessment first to create a draft.", "Crear draft desde un diagnóstico Atlas": "Create draft from an Atlas assessment",
    "Diagnóstico Atlas de origen": "Source Atlas assessment", "Qué define el alcance": "Scope authority", "Crear draft": "Create draft",
    "Todo decidido. Podés emitir la release y prepararla para la plataforma en **Release y entrega a la plataforma**.": "All decisions made. Issue the release and prepare it for the platform in **Release and platform delivery**.",
    "Elemento a decidir": "Element to review", "Todavía no hay elementos en el modelo canónico.": "No canonical model elements yet.", "Agregar elemento": "Add element",
    "No se detectaron duplicados.": "No duplicates found.", "Rechazar duplicados pendientes": "Reject pending duplicates", "Aplicar": "Apply",
    "Emití una primera release para comparar contra una línea base.": "Issue a first release to compare against a baseline.", "Comparar": "Compare", "Release base": "Baseline release",
    "**1. Emitir release**": "**1. Issue release**", "**2. Entregar a la plataforma destino** (ruta preferida)": "**2. Deliver to the target platform** (preferred route)",
    "Genera archivos que la plataforma del cliente importa en su propia ontología: Fabric IQ (ítem Ontology y Data Agent) o Databricks (Pages, metric views, Unity Catalog y Genie). Indica qué se implementa ahí y qué queda en ONTO como plan B. No usa credenciales ni publica.": "Generates files for the client platform to import into its own ontology: Fabric IQ (Ontology item and Data Agent) or Databricks (Pages, metric views, Unity Catalog and Genie). Shows what is implemented there and what remains in ONTO as a fallback. Does not use credentials or publish.",
    "No quedan candidatos pendientes con este filtro.": "No pending candidates match this filter.", "Sin resultados.": "No results.", "Nota común": "Shared note",
    "Confirmo que revisé la lista filtrada": "I confirm I reviewed the filtered list", "Guardar decisión": "Save decision", "Responsable de negocio (opcional)": "Business owner (optional)",
    "Definición o regla": "Definition or rule", "Candidatos vinculados (dos para relación o vínculo con fuente; uno para los demás)": "Linked candidates (two for relationships or source bindings; one for other types)",
    "Agregar para revisión": "Add for review", "Hacen falta al menos dos releases.": "At least two releases are required.", "Release inicial": "Initial release", "Release final": "Final release",
    "Responsable de la release": "Release owner", "Nota de release": "Release note", "Emitir release": "Issue release", "Emití una release para preparar un paquete.": "Issue a release to prepare a package.",
    "Plataforma destino": "Target platform", "Responsable del paquete": "Package owner", "Generar paquete para la plataforma": "Generate platform package",
    "Dónde queda": "Destination", "Confianza": "Confidence", "Vínculos": "Bindings", "Confirmá la revisión antes de aplicar.": "Confirm the review before applying.", "Creada": "Created",
    "Revisión de candidatos": "Candidate review", "Consolidación": "Consolidation", "Release y entrega a la plataforma": "Release and platform delivery",
    "Respondida": "Answered", "Abstención": "Abstained", "Argos · Investigación de negocio": "Argos · Business investigation", "Preguntá sobre el negocio": "Ask about the business",
    "**Consultas autorizadas en esta release**": "**Authorized queries in this release**", "**Batería de evaluación**": "**Evaluation suite**",
    "Define qué debe responder Argos y de qué debe abstenerse. Cada ejecución valida el estado esperado y, si corresponde, la evidencia recuperada.": "Defines what Argos should answer and when it should abstain. Each execution validates the expected status and, where applicable, the retrieved evidence.",
    "Preparar batería base": "Prepare baseline suite", "Un caso por línea: pregunta | answered o abstained | evidencia esperada (opcional)": "One case per line: question | answered or abstained | expected evidence (optional)",
    "Ejecutar batería": "Run suite", "Casos": "Cases", "Correctos": "Passed", "Fallidos": "Failed", "Ver respuesta de un caso": "View case response",
    "Argos todavía no está disponible: falta emitir una release aprobada en Nexo.": "Argos is not available yet: issue an approved release in Nexo first.",
    "**¿Por dónde empezar?**": "**Where to start?**", "Limpiar conversación": "Clear conversation", "Evidencia y trazabilidad": "Evidence and traceability",
    "La release no tiene consultas de datos; Argos responde solo con el conocimiento aprobado.": "The release has no data queries; Argos answers using approved knowledge only.",
    "Argos está consultando el contexto y los datos permitidos…": "Argos is querying the context and authorized data…",
    "Escribí una pregunta sobre el negocio. Ejemplo: ¿Qué es un cliente activo?": "Ask a business question. Example: What is an active customer?",
    "Correcto": "Passed", "Esperado": "Expected", "Obtenido": "Actual", "Evidencia": "Evidence", "Consulta": "Query", "Parámetros": "Parameters",
    "Máx. filas": "Max. rows", "Pregunta de ejemplo": "Example question", "Cargá al menos un caso.": "Enter at least one case.", "Ejecutando batería…": "Running suite…",
    "Conversación": "Conversation", "Analistas": "Analysts", "modo local determinista": "local deterministic mode",
    "Indicá tu nombre en **Revisor/a de esta sesión** (barra lateral) para registrar decisiones.": "Enter your name in **Session reviewer** (sidebar) to record decisions.",
    "Administración del contexto seleccionado: {v0}": "Manage the selected context: {v0}",
    "{v0}: {v1}": "{v0}: {v1}", "Conceptos: {v0}": "Concepts: {v0}", "Relaciones: {v0}": "Relationships: {v0}", "Avisos: {v0}": "Warnings: {v0}",
    "{v0} | {v1}": "{v0} | {v1}", "{v0} --{v1}--> {v2}": "{v0} --{v1}--> {v2}", "{v0} · {v1}": "{v0} · {v1}",
    "Importacion BIM lista: {v0} tablas, {v1} columnas, {v2} medidas y {v3} relaciones detectadas.": "BIM import complete: {v0} tables, {v1} columns, {v2} measures and {v3} relationships detected.",
    "Perfil '{v0}' guardado para este proyecto": "Profile '{v0}' saved for this project", "Conexion read-only OK: {v0} / {v1}": "Read-only connection OK: {v0} / {v1}",
    "Linea invalida: {v0}": "Invalid line: {v0}",
    "Banco de prueba del conocimiento aprobado antes de implementarlo en la plataforma del cliente, y runtime de plan B para lo que la plataforma no pueda cubrir. Responde solo con la release del {v0} y consultas autorizadas. Motor: {v1}.": "Test bench for approved knowledge before implementation on the client platform, and fallback runtime for what the platform cannot cover. Answers using only the release from {v0} and authorized queries. Engine: {v1}.",
    "Estado: {v0} · Registro: {v1}": "Status: {v0} · Record: {v1}", "Paquete de evaluación: {v0}": "Evaluation package: {v0}",
    "Consulta: {v0} · {v1} · {v2} fila(s)": "Query: {v0} · {v1} · {v2} row(s)", "Datos ({v0} fila(s))": "Data ({v0} row(s))", "Motor: {v0}": "Engine: {v0}",
    "{v0} | {v1} | {v2}": "{v0} | {v1} | {v2}",
    "Cliente **{v0}** · Dominio **{v1}** · Producto de datos **{v2}**. El diagnóstico es determinista (sin LLM) y no aprueba una ontología ni publica en sistemas externos.": "Client **{v0}** · Domain **{v1}** · Data product **{v2}**. The assessment is deterministic (no LLM); it does not approve an ontology or publish to external systems.",
    "{v0} / 5": "{v0} / 5", "{v0} altas": "{v0} high", "Inicial: {v0} · Final: {v1}": "Initial: {v0} · Final: {v1}",
    "Alcance: {v0} · Cálculo: {v1}": "Scope: {v0} · Calculation: {v1}", "Respaldados: {v0} · Faltantes: {v1}": "Supported: {v0} · Missing: {v1}",
    "Responsable propuesto: {v0} · Por confirmar · Prioridad: {v1}": "Proposed owner: {v0} · To be confirmed · Priority: {v1}",
    "Alcance: {v0} · Criterios: {v1} · Sin evaluación explicativa todavía.": "Scope: {v0} · Criteria: {v1} · No explanatory evaluation yet.",
    "Siguiente paso: {v0}": "Next step: {v0}", "Quitar '{v0}' y sus objetos inventariados (se guarda un snapshot antes)": "Remove '{v0}' and its inventoried objects (a snapshot is saved first)",
    "Motor de extracción: {v0} · {v1}": "Extraction engine: {v0} · {v1}", "No se detectaron {v0}.": "No {v0} detected.",
    "Proveedor: {v0} · Modelo: {v1} · Política: {v2}": "Provider: {v0} · Model: {v1} · Policy: {v2}",
    "**{v0}**\n\nInicial: **{v1}**  \nFinal: **{v2}**": "**{v0}**\n\nInitial: **{v1}**  \nFinal: **{v2}**",
    "En alcance: {v0} → {v1}": "In scope: {v0} → {v1}",
    "{v0} · Modo: {v1} · Proveedor: {v2} · Modelo: {v3} · Prompt: {v4}": "{v0} · Mode: {v1} · Provider: {v2} · Model: {v3} · Prompt: {v4}",
    "Llamadas: {v0} / {v1} · Reutilizado: {v2}": "Calls: {v0} / {v1} · Reused: {v2}",
    "{v0} explicados / {v1} en alcance · {v2} evaluados · {v3} fallos": "{v0} explained / {v1} in scope · {v2} evaluated · {v3} failures",
    "Elementos visibles: {v0} / {v1} en alcance. Los filtros no cambian el denominador.": "Visible elements: {v0} / {v1} in scope. Filters do not change the denominator.",
    "{v0} · {v1} · {v2}": "{v0} · {v1} · {v2}", "{v0}/5 · {v1} brechas": "{v0}/5 · {v1} gaps",
    "{v0} caso(s) de uso": "{v0} use case(s)", "{v0}/{v1} sistemas inventariados": "{v0}/{v1} systems inventoried",
    "{v0} documento(s) analizados": "{v0} document(s) analyzed", "{v0} documento(s), sin analizar": "{v0} document(s), not analyzed",
    "{v0} **{v1}**": "{v0} **{v1}**", "{v0} tablas/vistas y {v1} columnas leídas.": "{v0} tables/views and {v1} columns read.",
    "Diferencia: {v0:+g} pp": "Difference: {v0:+g} pp", "{v0} / {v1}": "{v0} / {v1}",
    "Entidades presentes en un solo sistema ({v0})": "Entities in a single system ({v0})", "Conexión confirmada: {v0} · {v1}": "Connection confirmed: {v0} · {v1}",
    "{v0}: {v1}/5": "{v0}: {v1}/5", "{v0}: {v1} tablas y {v2} columnas.": "{v0}: {v1} tables and {v2} columns.",
    "Fabric: {v0} objetos nuevos incorporados.": "Fabric: {v0} new objects added.", "{v0} ({v1})": "{v0} ({v1})", "Paquete local: {v0}": "Local package: {v0}",
    "{v0} · {v1} · {v2} pendientes de {v3}": "{v0} · {v1} · {v2} pending out of {v3}", "{v0} pendientes": "{v0} pending",
    "{v0} · {v1} · confianza {v2}": "{v0} · {v1} · confidence {v2}", "Modo: {v0} · {v1} grupo(s) · {v2} candidatos analizados": "Mode: {v0} · {v1} group(s) · {v2} candidates analyzed",
    "**Canónico:** {v0}  \n**Posibles duplicados:** {v1}": "**Canonical:** {v0}  \n**Possible duplicates:** {v1}",
    "Descargar paquete para {v0} (.zip)": "Download {v0} package (.zip)", "También guardado en: {v0}": "Also saved at: {v0}",
    "{v0} de {v1} decisiones tomadas": "{v0} of {v1} decisions made",
    "Siguiente paso: decidir {v0} elemento(s) pendiente(s). La release se habilita cuando no quede ninguno.": "Next step: review {v0} pending element(s). The release becomes available when none remain.",
    "Evidencia · {v0} · {v1}": "Evidence · {v0} · {v1}", "Última decisión: {v0} · {v1}": "Latest decision: {v0} · {v1}",
    "Decisión masiva sobre {v0} pendiente(s) visibles": "Bulk decision on {v0} visible pending item(s)",
    "{v0} vínculos propuestos; {v1} ambiguos omitidos.": "{v0} bindings proposed; {v1} ambiguous matches omitted.",
    "Faltan {v0} decisiones; la release está bloqueada.": "{v0} decisions remain; the release is blocked.", "{v0} + {v1} · {v2}": "{v0} + {v1} · {v2}",
    "Release {v0} creada. Siguiente paso: prepararla para la plataforma destino.": "Release {v0} created. Next step: prepare it for the target platform.", "{v0} {v1}": "{v0} {v1}",
    "No evaluable": "Not assessable", "Sin casos de uso": "No use cases", "Sin sistemas": "No systems", "Desactualizado": "Outdated", "Generado": "Generated",
    "Sí": "Yes", "No": "No", "Definiciones": "Definitions", "Reglas": "Rules", "Entidades vinculadas": "Linked entities", "Preguntas para taller": "Workshop questions",
    "Transición para revisar": "Transition to review", "Evidencia inicial": "Initial evidence", "Evidencia final": "Final evidence", "Contradicción": "Contradiction",
    "Grupo sin elementos en alcance: no evaluable.": "No elements in scope: not assessable.", "Sin elementos para estos filtros.": "No elements match these filters.",
    "Caso de uso (por sistema)": "Use case (by system)", "Por confirmar": "To be confirmed", "Criterio de cierre: ": "Closure criterion: ", "Motivo: ": "Reason: ",
    "Muestra para revisión: ": "Review sample: ", "sin nota": "no note", "sin dominio": "no domain",
    "significado": "meaning", "granularidad": "grain", "identificacion": "identification", "extremos": "endpoints",
    "cardinalidad_si_aplica": "cardinality if applicable", "formula": "formula", "filtros_y_exclusiones": "filters and exclusions", "valores_o_unidad": "values or unit",
    "extremos de la relacion": "relationship endpoints", "cardinalidad o no aplicabilidad": "cardinality or non-applicability", "filtros y exclusiones": "filters and exclusions", "valores o unidad": "values or unit",
    "Documento": "Document", "Agregados": "Added", "Eliminados": "Removed", "Cambiados": "Changed",
    "Este draft vs. una release": "This draft vs. a release", "Dos releases": "Two releases", "El canónico no se aprueba automáticamente.": "The canonical item is not approved automatically.",
    "Formato inválido en líneas: ": "Invalid format on lines: ",
    "¿Qué es Cliente Activo? | answered | Cliente Activo\n¿Qué planeta es más grande? | abstained |": "What is an active customer? | answered | Active customer\nWhich planet is largest? | abstained |",
    "Hay sistemas declarados sin metadata; el universo disponible es incompleto.": "Declared systems lack metadata; the available inventory is incomplete.",
    "Sin inventario tecnico: universo provisional, no se puede medir todo el dominio.": "No technical inventory: provisional scope; the entire domain cannot be measured.",
    "Hay elementos sin sistema identificado; se conservan en el universo pendiente de asignacion.": "Some elements have no identified system; they remain in the inventory awaiting assignment.",
    "Hay casos de uso sin sistemas vinculados.": "Some use cases have no linked systems.",
    "Hay elementos sin caso de uso vinculado; se conservan como pendientes.": "Some elements have no linked use case; they remain pending.",
    "Los vinculos por sistema indican alcance, no relevancia semantica confirmada.": "System links indicate scope, not confirmed semantic relevance.",
    "Los casos de uso se vinculan por sistema, no por relevancia semantica confirmada.": "Use cases are linked by system, not by confirmed semantic relevance.",
    "Hay IDs de fragmentos ambiguos; sus referencias no respaldan clasificaciones.": "Some chunk IDs are ambiguous; their references do not support classifications.",
    "Hay elementos sin evaluar o con fallos; no demuestran ausencia de explicacion.": "Some elements are not evaluated or failed; this does not demonstrate a missing explanation.",
    "Valida IDs, citas y requisitos; no valida automaticamente el respaldo semantico ni aprueba conocimiento.": "Validates IDs, quotes and requirements; does not automatically validate semantic support or approve knowledge.",
    "Ambos assessments deben conservar una matriz explicativa.": "Both assessments must have an explanatory matrix.",
    "Cambios observados, no causalidad probada ni aprobacion. Los cierres requieren revision humana. Las evidencias comparadas son las citadas; duplicar texto no agrega respaldo.": "Observed changes, not proven causality or approval. Closures require human review. Only cited evidence is compared; duplicating text does not add support.",
    "Sin sistema identificado": "No identified system", "Sin clasificacion estructurada.": "No structured classification.",
    "Falta el metodo de evaluacion.": "Evaluation method is missing.", "La evaluacion no se completo.": "Evaluation did not complete.",
    "ID de fragmento ambiguo: no puede respaldar la clasificacion.": "Ambiguous chunk ID: cannot support classification.",
    "Aspecto fuera de los requisitos del elemento.": "Aspect is outside the element requirements.",
    "Contradiccion sin motivo o indicadores invalidos.": "Contradiction has no reason or invalid flags.",
    "Vinculo estructural de propiedades; se evalua con la propiedad.": "Structural property link; evaluated with the property.",
    "Una evaluacion completa y trazable clasifica el elemento; no basta adjuntar otro documento.": "A complete, traceable evaluation classifies the element; attaching another document is not enough.",
    "Una fuente autorizada explica la definicion aplicable; al reevaluar no queda contradiccion material pendiente.": "An authorized source explains the applicable definition; re-evaluation leaves no unresolved material contradiction.",
    "La nueva evidencia respalda los aspectos faltantes con citas verificables y permite reevaluar el elemento.": "New evidence supports the missing aspects with verifiable quotes and allows re-evaluation of the element.",
    "Reintentar el analisis y revisar el error registrado.": "Retry the analysis and review the recorded error.",
    "Completar el contraste de la evidencia disponible.": "Complete the assessment of the available evidence.",
    "Confirmar la definicion aplicable y resolver las contradicciones documentadas.": "Confirm the applicable definition and resolve documented contradictions.",
    "Solicitar documentacion que explique: {aspects}.": "Request documentation explaining: {aspects}.",
    "Clasificacion estructurada: {state}.": "Structured classification: {state}.",
    "alta": "high", "media": "medium", "baja": "low", "draft": "draft", "review": "under review", "approved": "approved",
    "rejected": "rejected", "pending_review": "pending review", "explained": "explained", "partial": "partial", "unexplained": "unexplained", "contradictory": "contradictory",
    "Ejemplo: Rentabilidad por cliente": "Example: Profitability by customer", "¿Qué clientes generan más margen?": "Which customers generate the highest margin?",
    "Ejemplo: ERP operativo": "Example: Operational ERP", "Nombre o definición": "Name or definition",
    "Motor de extracción: reglas locales (sin LLM, sin costo).": "Extraction engine: local rules (no LLM, no cost).",
    "Host": "Host", "Password": "Password", "Release": "Release", "Atlas": "Atlas", "Nexo": "Nexo", "Argos": "Argos",
    "KPIs": "KPIs", "KPI": "KPI", "Error": "Error", "Adapter": "Adapter", "SHA-256": "SHA-256", "ID": "ID",
    "Cobertura de objetos tecnicos extraidos.": "Coverage of extracted technical objects.",
    "Documentacion y contexto funcional disponible.": "Available documentation and business context.",
    "Cruce basal entre fuentes tecnicas y funcionales.": "Baseline mapping between technical and business sources.",
    "Evidencia, casos de uso y estructura disponibles para iniciar revision.": "Evidence, use cases and structure available to begin review.",
    "Planillas / archivos": "Spreadsheets / files", "Otro": "Other",
    "Nombre de la ontologia (opcional)": "Ontology name (optional)",
    "Catalogo por defecto de Unity Catalog (opcional)": "Default Unity Catalog catalog (optional)",
    "ID del SQL warehouse para Genie (opcional)": "SQL warehouse ID for Genie (optional)",
    "Se implementa en la plataforma": "Implemented in the platform",
    "Se implementa en la plataforma, falta completar un dato": "Implemented in the platform; a required value is missing",
    "Se implementa como instruccion o documento del agente": "Implemented as an agent instruction or document",
    "Fuera del alcance de la plataforma (puente o plan B)": "Outside the platform scope (bridge or fallback)",
    "{v0} explicaciones inferidas por el modelo; no cuentan como cobertura documental.": "{v0} model-inferred explanations; they do not count as documentary coverage.",
    "Explicacion inferida: {aspect}": "Inferred explanation: {aspect}",
    "Inferida en grado importante por el modelo. No confirmada documentalmente; requiere revision humana.": "Substantially inferred by the model. Not confirmed by documents; requires human review.",
    "**Fundamento de la inferencia**": "**Basis of the inference**",
    "**Supuestos por confirmar**": "**Assumptions to confirm**",
    "**Validaciones pendientes**": "**Pending validations**",
    "Contexto que motivo la hipotesis, no prueba: {chunk_id}": "Context motivating the hypothesis, not proof: {chunk_id}",
}


def language() -> str:
    selected = st.session_state.get(LANGUAGE_KEY, "es")
    return selected if selected in LANGUAGES else "es"


def t(message: str, **values: object) -> str:
    translated = EN.get(message, message) if language() == "en" else message
    return translated.format(**values) if values else translated


class LocalizedLabels(Mapping):
    def __init__(self, labels: dict):
        self.labels = labels

    def __getitem__(self, key):
        return t(self.labels[key])

    def __iter__(self):
        return iter(self.labels)

    def __len__(self):
        return len(self.labels)


def localize_rows(rows):
    return [{t(key): value for key, value in row.items()} for row in rows]


def option_labels(options, formatter=t):
    labels = {option: formatter(option) for option in options}
    return labels.get


def localized_tabs(source_labels: list[str], key: str):
    labels = [t(label) for label in source_labels]
    selected = st.session_state.get(key)
    index = next((index for index, source in enumerate(source_labels)
                  if selected in (source, EN.get(source, source))), 0)
    if selected is not None and selected != labels[index]:
        st.session_state[key] = labels[index]
    return st.tabs(labels, default=labels[index], key=key, on_change="rerun")


def request_text(request: dict) -> str:
    actions = {
        "retry_analysis": "Reintentar el analisis y revisar el error registrado.",
        "evaluate": "Completar el contraste de la evidencia disponible.",
        "resolve_contradiction": "Confirmar la definicion aplicable y resolver las contradicciones documentadas.",
    }
    if language() == "es":
        return request["request"]
    if request["action"] == "request_evidence":
        required = t("Solicitar documentacion que explique: {aspects}.",
                     aspects=", ".join(t(aspect) for aspect in request["missing_aspects"]))
    else:
        required = t(actions[request["action"]])
    return f"{request['element_name']}: {required}"


def reason_text(message: str) -> str:
    for state in ("explained", "partial", "unexplained", "contradictory"):
        if message == f"Clasificacion estructurada: {state}.":
            return t("Clasificacion estructurada: {state}.", state=t(state))
    return t(message)


def _preserve_input_values() -> None:
    """Freeze decoded selections before Streamlit reinterprets translated labels."""
    for key in list(st.session_state):
        value = st.session_state[key]
        if isinstance(value, str) or isinstance(value, list) and value and all(isinstance(item, str) for item in value):
            st.session_state[key] = value


def render_language_selector() -> None:
    if LANGUAGE_KEY not in st.session_state:
        requested = st.query_params.get("lang", "es")
        st.session_state[LANGUAGE_KEY] = requested if requested in LANGUAGES else "es"
    st.sidebar.selectbox("Idioma / Language", list(LANGUAGES), format_func=LANGUAGES.get, key=LANGUAGE_KEY,
                         on_change=_preserve_input_values)
    if st.query_params.get("lang") != language():
        st.query_params["lang"] = language()