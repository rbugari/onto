from __future__ import annotations


LOCAL_SYNTHETIC_QUERY_ROWS = {
    "sales_by_customer": [
        {
            "customer_id": 42,
            "customer_name": "Acme Sur",
            "order_count": 3,
            "net_sales": 12500.0,
            "gross_margin": 3100.0,
        },
        {
            "customer_id": 7,
            "customer_name": "Delta Retail",
            "order_count": 2,
            "net_sales": 4800.0,
            "gross_margin": 1120.0,
        },
    ]
}


class LocalDataAdapterError(RuntimeError):
    """Controlled error for the allowlisted local synthetic data adapter."""


def execute_local_synthetic_query(
    template_id: str,
    parameters: tuple[object, ...] = (),
    max_rows: int = 100,
) -> dict[str, object]:
    clean_template_id = template_id.strip().lower()
    if clean_template_id != "sales_by_customer":
        raise ValueError("Template local no soportado")
    if len(parameters) != 1 or not isinstance(parameters[0], int):
        raise ValueError("sales_by_customer requiere customer_id entero")
    if not 1 <= max_rows <= 10_000:
        raise ValueError("El limite de filas esta fuera del rango permitido")

    customer_id = parameters[0]
    rows = [
        row for row in LOCAL_SYNTHETIC_QUERY_ROWS[clean_template_id]
        if row["customer_id"] == customer_id
    ][:max_rows]
    return {
        "status": "local_synthetic_query",
        "query_name": clean_template_id,
        "template_id": clean_template_id,
        "parameters": list(parameters),
        "operation": "SELECT",
        "binding": "FactSales",
        "source": "synthetic-demo-data",
        "rows": rows,
    }
