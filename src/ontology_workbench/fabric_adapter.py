from __future__ import annotations

import os
import struct
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


FABRIC_TOKEN_SCOPE = "https://database.windows.net//.default"
FABRIC_CACHE_NAME = "agente-new-fabric"
FABRIC_QUERY_TEMPLATES = {
    "risk_summary": (
        "SELECT COUNT_BIG(*) AS total_rows, COUNT(DISTINCT sic) AS distinct_sic, "
        "MAX(fecha_calculo) AS latest_calculation FROM gold_sic.fact_riesgo"
    ),
    "risk_levels": (
        "SELECT TOP (10) riesgo_final_texto, COUNT_BIG(*) AS total_rows "
        "FROM gold_sic.fact_riesgo GROUP BY riesgo_final_texto ORDER BY total_rows DESC"
    ),
    "impact_summary": (
        "SELECT COUNT_BIG(*) AS total_rows, COALESCE(SUM(reales), 0) AS reales, "
        "COALESCE(SUM(proxies), 0) AS proxies, COALESCE(SUM(pendientes), 0) AS pendientes, "
        "COALESCE(SUM(no_disponibles), 0) AS no_disponibles "
        "FROM gold_sic.fact_impacto_bloque"
    ),
    "impact_statuses": (
        "SELECT TOP (10) tipo_valor, estado, usa_default, COUNT_BIG(*) AS total_rows "
        "FROM gold_sic.fact_impacto GROUP BY tipo_valor, estado, usa_default "
        "ORDER BY total_rows DESC"
    ),
}
FABRIC_QUERY_BINDING_TABLES = {
    "risk_summary": "gold_sic.fact_riesgo",
    "risk_levels": "gold_sic.fact_riesgo",
    "impact_summary": "gold_sic.fact_impacto_bloque",
    "impact_statuses": "gold_sic.fact_impacto",
}


class FabricConnectionError(RuntimeError):
    """Controlled error for the delegated, read-only Fabric adapter."""


@dataclass(frozen=True)
class FabricSettings:
    server: str
    database: str
    tenant_id: str
    client_id: str
    auth_method: str
    config_path: Path
    auth_record_path: Path


def load_fabric_settings() -> FabricSettings:
    root_dir = Path(__file__).resolve().parents[2]
    local_env = dotenv_values(root_dir / ".env")
    config_value = (
        os.getenv("ONTO_FABRIC_CONFIG_PATH", "").strip()
        or str(local_env.get("ONTO_FABRIC_CONFIG_PATH", "")).strip()
        or os.getenv("ONTO_LLM_CONFIG_PATH", "").strip()
        or str(local_env.get("ONTO_LLM_CONFIG_PATH", "")).strip()
    )
    if not config_value:
        raise FabricConnectionError(
            "Configure ONTO_FABRIC_CONFIG_PATH con el .env de Fabric compartido."
        )
    config_path = Path(config_value).expanduser()
    if not config_path.exists():
        raise FabricConnectionError("No se encontró el archivo de configuración Fabric compartido.")
    shared = dotenv_values(config_path)
    auth_mode = _value(shared, "FABRIC_AUTH_MODE").casefold()
    if auth_mode != "interactive_browser":
        raise FabricConnectionError(
            "El conector ONTO requiere FABRIC_AUTH_MODE=interactive_browser para operar con identidad delegada."
        )
    auth_record_value = (
        os.getenv("ONTO_FABRIC_AUTH_RECORD_PATH", "").strip()
        or str(local_env.get("ONTO_FABRIC_AUTH_RECORD_PATH", "")).strip()
    )
    auth_record_path = (
        Path(auth_record_value).expanduser()
        if auth_record_value
        else config_path.parent / "data" / "fabric-auth-record.json"
    )
    settings = FabricSettings(
        server=_value(shared, "FABRIC_WAREHOUSE_SERVER"),
        database=_value(shared, "FABRIC_WAREHOUSE_DATABASE"),
        tenant_id=_value(shared, "FABRIC_TENANT_ID"),
        client_id=_value(shared, "FABRIC_CLIENT_ID"),
        auth_method=_value(shared, "FABRIC_AUTH_METHOD", "interactive_browser").casefold(),
        config_path=config_path,
        auth_record_path=auth_record_path,
    )
    if not settings.server or not settings.database:
        raise FabricConnectionError("Faltan endpoint o base de datos de Fabric en la configuración compartida.")
    if settings.auth_method not in {"interactive_browser", "device_code"}:
        raise FabricConnectionError("FABRIC_AUTH_METHOD debe ser interactive_browser o device_code.")
    return settings


def fabric_connection_check() -> dict[str, str]:
    settings = load_fabric_settings()
    with _connection(settings) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT SUSER_SNAME() AS user_name, DB_NAME() AS database_name")
        row = cursor.fetchone()
    return {
        "status": "connected_read_only",
        "database": str(row.database_name),
        "identity": str(row.user_name),
        "server": settings.server,
    }


def execute_fabric_read_only_query(query_name: str) -> dict[str, object]:
    """Execute one named, aggregate-only query; arbitrary SQL is never accepted."""
    clean_name = query_name.strip().lower()
    query = FABRIC_QUERY_TEMPLATES.get(clean_name)
    if query is None:
        raise ValueError("Consulta Fabric no soportada")
    settings = load_fabric_settings()
    with _connection(settings) as connection:
        cursor = connection.cursor()
        cursor.execute(query)
        columns = [str(item[0]) for item in cursor.description]
        rows = [
            {
                column: value.isoformat() if hasattr(value, "isoformat") else value
                for column, value in zip(columns, row)
            }
            for row in cursor.fetchall()
        ]
    return {
        "status": "connected_read_only_query",
        "query_name": clean_name,
        "operation": "SELECT",
        "server": settings.server,
        "database": settings.database,
        "rows": rows,
    }


def discover_fabric_metadata(
    max_tables: int = 100,
    max_columns: int = 2_000,
    table_name_pattern: str = "",
    schema_name: str = "",
) -> dict[str, object]:
    """Inventory only schema metadata; this adapter never reads business rows."""
    if not 1 <= max_tables <= 500 or not 1 <= max_columns <= 10_000:
        raise ValueError("Los límites de inventario Fabric están fuera del rango permitido")
    settings = load_fabric_settings()
    pattern = table_name_pattern.strip()
    schema = schema_name.strip()
    table_filter = ""
    parameters: list[object] = []
    if schema:
        table_filter += " AND TABLE_SCHEMA = ?"
        parameters.append(schema)
    if pattern:
        table_filter += " AND TABLE_NAME LIKE ?"
        parameters.append(f"%{pattern}%")
    with _connection(settings) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT TOP (?) TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE "
            "FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE IN ('BASE TABLE', 'VIEW') "
            + table_filter
            + " ORDER BY TABLE_SCHEMA, TABLE_NAME",
            max_tables,
            *parameters,
        )
        tables = [
            {"schema": str(row.TABLE_SCHEMA), "name": str(row.TABLE_NAME), "type": str(row.TABLE_TYPE)}
            for row in cursor.fetchall()
        ]
        cursor.execute(
            "SELECT TOP (?) TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, ORDINAL_POSITION "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE 1=1"
            + table_filter
            + " ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION",
            max_columns,
            *parameters,
        )
        columns = [
            {
                "schema": str(row.TABLE_SCHEMA),
                "table": str(row.TABLE_NAME),
                "name": str(row.COLUMN_NAME),
                "data_type": str(row.DATA_TYPE),
                "nullable": str(row.IS_NULLABLE),
                "ordinal_position": int(row.ORDINAL_POSITION),
            }
            for row in cursor.fetchall()
        ]
    return {
        "format": "onto-fabric-metadata-discovery-v0.1",
        "mode": "read_only_metadata",
        "server": settings.server,
        "database": settings.database,
        "tables": tables,
        "columns": columns,
        "limits": {"max_tables": max_tables, "max_columns": max_columns},
        "table_name_pattern": pattern,
        "schema_name": schema,
    }


def _connection(settings: FabricSettings):
    try:
        import pyodbc
    except ImportError as exc:
        raise FabricConnectionError("Falta pyodbc. Instale los requisitos de ONTO.") from exc
    credential = _credential(settings)
    try:
        access_token = credential.get_token(FABRIC_TOKEN_SCOPE).token
        token_bytes = access_token.encode("utf-16-le")
        token_attribute = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)
        connection_string = (
            "Driver={ODBC Driver 18 for SQL Server};"
            f"Server=tcp:{settings.server},1433;"
            f"Database={settings.database};Encrypt=yes;TrustServerCertificate=no;"
        )
        return pyodbc.connect(
            connection_string, attrs_before={1256: token_attribute}, timeout=30
        )
    except Exception as exc:
        raise FabricConnectionError(str(exc)) from exc


def _credential(settings: FabricSettings):
    try:
        from azure.identity import (
            AuthenticationRecord,
            DeviceCodeCredential,
            InteractiveBrowserCredential,
            TokenCachePersistenceOptions,
        )
    except ImportError as exc:
        raise FabricConnectionError("Falta azure-identity. Instale los requisitos de ONTO.") from exc
    options: dict[str, object] = {
        "cache_persistence_options": TokenCachePersistenceOptions(
            name=FABRIC_CACHE_NAME, allow_unencrypted_storage=False
        )
    }
    if settings.tenant_id:
        options["tenant_id"] = settings.tenant_id
    if settings.client_id:
        options["client_id"] = settings.client_id
    if settings.auth_record_path.exists():
        try:
            options["authentication_record"] = AuthenticationRecord.deserialize(
                settings.auth_record_path.read_text(encoding="utf-8")
            )
        except Exception:
            pass
    if settings.auth_method == "device_code":
        return DeviceCodeCredential(**options)
    return InteractiveBrowserCredential(**options)


def _value(values: dict[str, str | None], key: str, default: str = "") -> str:
    return str(values.get(key, default) or default).strip()
