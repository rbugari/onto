"""Spanish labels shared by the Streamlit screens."""
from __future__ import annotations

SEVERITY_LABELS = {"high": "Alta", "medium": "Media", "low": "Baja"}
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

GAP_CATEGORY_LABELS = {
    "alcance": "Alcance",
    "fuentes": "Fuentes",
    "entre_sistemas": "Entre sistemas",
    "negocio": "Negocio",
    "gobierno": "Gobierno",
}

DIMENSION_LABELS = {
    "semantic_metadata": "Metadata técnica",
    "business_context": "Contexto de negocio",
    "semantic_business_linkage": "Vínculo técnico-negocio",
    "governance_traceability": "Gobierno y trazabilidad",
    "cross_source_alignment": "Alineación entre sistemas",
}

INTERPRETATION_LABELS = {
    "strong_foundation": "Base sólida",
    "partial_foundation": "Base parcial",
    "early_foundation": "Base inicial",
}

ATLAS_REVIEW_LABELS = {
    "pending_review": "Pendiente de revisión",
    "reviewed": "Revisado",
    "needs_follow_up": "Requiere seguimiento",
}

DECISION_LABELS = {
    "all": "Todos",
    "pending_review": "Pendiente",
    "approved": "Aprobado",
    "rejected": "Rechazado",
    "accepted_as_review_plan": "Aceptado como plan de revisión",
}

SOURCE_STATUS_LABELS = {"declared": "Sin metadata", "inventoried": "Inventariado"}

ACCESS_MODE_LABELS = {
    "external_file": "Archivo exportado",
    "live_read_only": "Conexión directa (solo lectura)",
}

PRIORITY_LABELS = {"alta": "Alta", "media": "Media", "baja": "Baja"}

DOCUMENT_TYPE_LABELS = {
    "functional_docs": "Documentación funcional",
    "technical_docs": "Documentación técnica",
    "kpi_definitions": "Definiciones de KPI",
    "data_dictionary": "Diccionario de datos",
    "process_docs": "Procesos",
    "architecture_docs": "Arquitectura",
    "bi_exports": "Exportaciones de BI",
    "misc": "Otros",
}

METADATA_FORMAT_HINTS = {
    "databricks": (
        "Exportá `system.information_schema.columns` (o `<catálogo>.information_schema.columns`) a CSV, "
        "o el resultado de `SHOW CREATE TABLE` a un archivo .sql."
    ),
    "mariadb": "Exportá la estructura con `mysqldump --no-data` (.sql). Las filas INSERT se ignoran.",
    "sqlserver": "Generate Scripts > Schema only (.sql), o INFORMATION_SCHEMA.COLUMNS exportado a CSV.",
    "postgres": "`pg_dump --schema-only` (.sql), o information_schema.columns exportado a CSV.",
    "snowflake": "`GET_DDL` (.sql), o INFORMATION_SCHEMA.COLUMNS exportado a CSV.",
    "oracle": "DDL exportado (.sql), o ALL_TAB_COLUMNS a CSV con table_name, column_name y data_type.",
    "powerbi": "model.bim, archivo TMDL o paquete PBIP comprimido (.zip).",
    "fabric": "Usá la conexión directa (más abajo) o exportá INFORMATION_SCHEMA.COLUMNS a CSV.",
    "files": "Describí la estructura de las planillas en un CSV con table_name, column_name y data_type.",
    "other": "DDL (.sql) o CSV con columnas table_name, column_name y data_type.",
}

METADATA_FILE_TYPES = ["sql", "ddl", "csv", "tsv", "txt", "bim", "json", "tmdl", "zip", "pbip"]


def short_timestamp(value: object) -> str:
    return str(value or "")[:16].replace("T", " ")
