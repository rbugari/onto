from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from dotenv import dotenv_values


MARIADB_QUERY_TEMPLATES = {
    "order_status_summary": (
        "SELECT estado, COUNT(*) AS cantidad FROM pedidos "
        "GROUP BY estado ORDER BY cantidad DESC LIMIT %s"
    ),
    "sales_summary": (
        "SELECT DATE_FORMAT(fecha, '%Y-%m') AS periodo, COUNT(*) AS pedidos, "
        "COALESCE(SUM(importeTotal), 0) AS ventas FROM pedidos "
        "WHERE LOWER(COALESCE(estado, '')) <> 'cancelado' "
        "GROUP BY DATE_FORMAT(fecha, '%Y-%m') ORDER BY periodo DESC LIMIT %s"
    ),
    "product_demand_by_year": (
        "SELECT pr.id AS producto_id, pr.codigo, pr.nombre, "
        "COALESCE(SUM(pi.cantidad), 0) AS unidades_solicitadas, "
        "COUNT(DISTINCT p.id) AS cantidad_pedidos "
        "FROM pedidos p "
        "INNER JOIN pedidoItems pi ON pi.pedidoId = p.id "
        "INNER JOIN productos pr ON pr.id = pi.productoId "
        "WHERE YEAR(p.fecha) = %s "
        "AND LOWER(COALESCE(p.estado, '')) <> 'cancelado' "
        "GROUP BY pr.id, pr.codigo, pr.nombre "
        "ORDER BY unidades_solicitadas DESC, cantidad_pedidos DESC, pr.id "
        "LIMIT %s"
    ),
    "customer_debt": (
        "SELECT c.id, c.nombre, c.deuda, "
        "COALESCE(SUM(CASE WHEN p.saldo > 0 THEN p.saldo ELSE 0 END), 0) AS saldo_pedidos "
        "FROM clientes c LEFT JOIN pedidos p ON p.cliente = c.id "
        "WHERE c.id = %s GROUP BY c.id, c.nombre, c.deuda"
    ),
    "product_availability": (
        "SELECT id, codigo, nombre, stockActual, stockReservado, "
        "COALESCE(stockActual, 0) - COALESCE(stockReservado, 0) AS stockDisponible "
        "FROM productos ORDER BY id LIMIT %s"
    ),
}


class MariaDBConnectionError(RuntimeError):
    """Controlled error for the delegated, read-only MariaDB adapter."""


@dataclass(frozen=True)
class MariaDBSettings:
    host: str
    user: str
    password: str
    database: str
    port: int
    config_path: Path | None


def load_mariadb_settings(config_path: Path | None = None) -> MariaDBSettings:
    root_dir = Path(__file__).resolve().parents[2]
    local_env = dotenv_values(root_dir / ".env")
    if config_path is not None:
        profile_path = Path(config_path).expanduser()
        if not profile_path.exists():
            raise MariaDBConnectionError(f"No existe el perfil MariaDB: {profile_path}")
        shared = dotenv_values(profile_path)
        config_value = str(profile_path)
        environment = {}
    else:
        config_value = (
            os.getenv("ONTO_MARIADB_CONFIG_PATH", "").strip()
            or str(local_env.get("ONTO_MARIADB_CONFIG_PATH", "")).strip()
        )
        shared = dotenv_values(Path(config_value).expanduser()) if config_value else {}
        environment = os.environ

    def value(name: str, default: str = "") -> str:
        fallback = shared.get(name, default)
        if config_path is None:
            fallback = environment.get(name, "") or local_env.get(name, fallback)
        return str(fallback).strip()

    host = value("DB_HOST")
    user = value("DB_USER")
    password = value("DB_PASSWORD")
    database = value("DB_NAME")
    if not host or not user or not password or not database:
        raise MariaDBConnectionError(
            "Configure DB_HOST, DB_USER, DB_PASSWORD y DB_NAME en un archivo local; no los incluya en el codigo."
        )
    try:
        port = int(value("DB_PORT", "3306"))
    except ValueError as exc:
        raise MariaDBConnectionError("DB_PORT debe ser numerico") from exc
    if not 1 <= port <= 65_535:
        raise MariaDBConnectionError("DB_PORT esta fuera de rango")
    return MariaDBSettings(host, user, password, database, port, Path(config_value) if config_value else None)


def execute_mariadb_read_only_query(
    query_name: str,
    parameters: tuple[object, ...] = (),
    max_rows: int = 100,
    config_path: Path | None = None,
) -> dict[str, object]:
    clean_name = query_name.strip().lower()
    query = MARIADB_QUERY_TEMPLATES.get(clean_name)
    if query is None:
        raise ValueError("Consulta MariaDB no soportada")
    if not 1 <= max_rows <= 10_000:
        raise ValueError("El limite de filas esta fuera del rango permitido")
    if clean_name in {"order_status_summary", "product_availability", "sales_summary"}:
        if len(parameters) not in {0, 1} or (parameters and not isinstance(parameters[0], int)):
            raise ValueError(f"{clean_name} requiere un limite entero opcional")
        query_parameters = (parameters[0] if parameters else max_rows,)
    elif clean_name == "product_demand_by_year":
        if len(parameters) != 1 or not isinstance(parameters[0], int) or not 2000 <= parameters[0] <= 2100:
            raise ValueError("product_demand_by_year requiere un año entero entre 2000 y 2100")
        query_parameters = (parameters[0], max_rows)
    elif clean_name == "customer_debt":
        if len(parameters) != 1 or not isinstance(parameters[0], int):
            raise ValueError("customer_debt requiere customer_id entero")
        query_parameters = parameters
    else:
        query_parameters = parameters

    settings = load_mariadb_settings(config_path)
    try:
        import mysql.connector
    except ImportError as exc:
        raise MariaDBConnectionError(
            "Falta mysql-connector-python para activar el adapter MariaDB."
        ) from exc

    try:
        connection = mysql.connector.connect(
            host=settings.host,
            port=settings.port,
            user=settings.user,
            password=settings.password,
            database=settings.database,
            connection_timeout=30,
        )
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SET SESSION TRANSACTION READ ONLY")
        cursor.execute(query, query_parameters)
        rows = cursor.fetchmany(max_rows)
        cursor.close()
        connection.close()
    except Exception as exc:
        raise MariaDBConnectionError("No se pudo ejecutar la consulta MariaDB read-only") from exc

    return {
        "status": "connected_read_only_query",
        "query_name": clean_name,
        "parameters": list(query_parameters),
        "operation": "SELECT",
        "server": settings.host,
        "database": settings.database,
        "rows": [
            {str(column): _json_safe_value(value) for column, value in dict(row).items()}
            for row in rows
        ],
    }


def _json_safe_value(value: object) -> object:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def check_mariadb_connection(config_path: Path | None = None) -> dict[str, str]:
    settings = load_mariadb_settings(config_path)
    try:
        import mysql.connector
    except ImportError as exc:
        raise MariaDBConnectionError(
            "Falta mysql-connector-python para comprobar el adapter MariaDB."
        ) from exc

    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(
            host=settings.host,
            port=settings.port,
            user=settings.user,
            password=settings.password,
            database=settings.database,
            connection_timeout=30,
        )
        cursor = connection.cursor()
        cursor.execute("SET SESSION TRANSACTION READ ONLY")
        cursor.execute("SELECT 1")
        cursor.fetchone()
    except Exception as exc:
        raise MariaDBConnectionError("No se pudo comprobar la conexion MariaDB read-only") from exc
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
    return {"status": "connected_read_only", "server": settings.host, "database": settings.database}
