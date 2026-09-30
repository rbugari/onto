"""Presentation hints for Argos results derived from the approved query catalog."""
from __future__ import annotations

from numbers import Number

# Fallback for releases published before catalogs carried `example_question`.
KNOWN_STARTER_QUESTIONS = {
    "risk_rule_sic": "¿Cuál es el riesgo de la regla 1 en el SIC 12?",
    "risk_sic": "¿Qué riesgos hay en el SIC 12?",
    "risk_levels": "¿Cómo se distribuyen los riesgos por nivel?",
    "risk_summary": "¿Cuántos riesgos hay en total?",
    "order_status_summary": "¿Cuántos pedidos hay por estado?",
    "sales_summary": "¿Cuál es la evolución de las ventas por mes?",
    "product_demand_by_year": "¿Cuáles fueron los 10 productos más demandados en 2025?",
    "product_availability": "¿Cuál es la disponibilidad de productos?",
    "sales_by_customer": "¿Cuántas ventas tiene el cliente 42?",
}
MAX_METRIC_FIELDS = 6
MAX_BAR_ROWS = 50


def starter_questions(catalog: dict[str, dict[str, object]], limit: int = 6) -> list[str]:
    questions: list[str] = []
    for query_name, specification in catalog.items():
        question = str(specification.get("example_question") or KNOWN_STARTER_QUESTIONS.get(query_name, "")).strip()
        if question and question not in questions:
            questions.append(question)
    return questions[:limit]


def infer_visualization(
    rows: list[dict[str, object]], specification: dict[str, object] | None = None
) -> dict[str, object] | None:
    """Use the catalog visualization when valid; otherwise pick metrics or a bar chart from the row shape."""
    if not rows:
        return None
    columns = list(rows[0].keys())
    configured = (specification or {}).get("visualization")
    if isinstance(configured, dict):
        if configured.get("type") == "metrics":
            fields = [field for field in configured.get("fields", []) if field in columns]
            if fields:
                return {"type": "metrics", "fields": fields}
        if configured.get("type") == "bar" and configured.get("x") in columns and configured.get("y") in columns:
            return {"type": "bar", "x": configured["x"], "y": configured["y"]}
    numeric = [column for column in columns if _is_numeric_column(rows, column)]
    labels = [column for column in columns if column not in numeric]
    if len(rows) == 1 and len(columns) <= MAX_METRIC_FIELDS:
        return {"type": "metrics", "fields": columns}
    if 2 <= len(rows) <= MAX_BAR_ROWS and labels and numeric:
        return {"type": "bar", "x": labels[0], "y": numeric[0]}
    return None


def _is_numeric_column(rows: list[dict[str, object]], column: str) -> bool:
    values = [row.get(column) for row in rows if row.get(column) is not None]
    return bool(values) and all(isinstance(value, Number) and not isinstance(value, bool) for value in values)
