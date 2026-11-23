"""What each target platform can reach, shared by Atlas (before approval) and the platform export (after approval)."""
from __future__ import annotations

# Source platforms each target can reach without extra integration work.
PLATFORM_REACH = {
    "fabric": {"fabric", "powerbi"},
    "databricks": {"databricks"},
}
BRIDGE_HINTS = {
    "fabric": (
        "Traer la fuente a OneLake: Mirroring (si el origen es compatible), shortcut, o Copy job/pipeline de Data Factory "
        "(bases on-premises como MySQL/MariaDB via on-premises data gateway). Si no es viable, esa parte queda en ONTO (plan B)."
    ),
    "databricks": (
        "Registrar la fuente con Lakehouse Federation (MySQL, PostgreSQL, SQL Server, entre otras; requiere conectividad de red) "
        "o ingerirla a Delta. Si no es viable, esa parte queda en ONTO (plan B)."
    ),
}
TARGET_LABELS = {"fabric": "Microsoft Fabric (Fabric IQ)", "databricks": "Databricks (Unity Catalog / Genie)"}


def reachable(source_platform: str, target: str) -> bool:
    return source_platform in PLATFORM_REACH.get(target, set())


def recommend_route(
    target: str, total: int, outside: int, tables_total: int, tables_outside: int
) -> tuple[str, str]:
    """Route A (all in the platform), B (mixed) or C (no table reachable) with its reason."""
    if not total:
        return "A", "La release no tiene elementos para entregar."
    if not outside:
        return "A", "Todo lo aprobado se puede implementar en la plataforma destino."
    if tables_total and tables_outside == tables_total:
        return "C", (
            f"Ninguna tabla de la release es alcanzable hoy por {TARGET_LABELS[target]}: los datos viven en otros sistemas. "
            f"La definicion se puede cargar, pero sin datos la plataforma no puede responder. Opciones: {BRIDGE_HINTS[target]}"
        )
    return "B", (
        f"{outside} elemento(s) dependen de sistemas que la plataforma no alcanza hoy. "
        f"Implementar el resto en {TARGET_LABELS[target]} y resolver esos con un puente o en ONTO (plan B)."
    )
