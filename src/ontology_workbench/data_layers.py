"""Bronze / Silver / Gold classification of tables: declared per system first, then inferred from names."""
from __future__ import annotations

import re

LAYERS = ("bronze", "silver", "gold")
LAYER_LABELS = {"bronze": "Bronze", "silver": "Silver", "gold": "Gold", "unknown": "Sin clasificar"}

_MARKERS = {
    "bronze": {"bronze", "raw", "landing", "ingest"},
    "silver": {"silver", "clean", "cleansed", "stg", "staging", "refined"},
    "gold": {"gold", "mart", "marts", "dm", "dim", "fact", "fct"},
}
_TOKEN_LAYER = {token: layer for layer, tokens in _MARKERS.items() for token in tokens}
# Semantic models are a consumption layer even when their names carry no marker.
_DEFAULT_BY_PLATFORM = {"powerbi": "gold"}


def table_layer(source_layer: str, platform: str, table_name: str) -> tuple[str, str]:
    """Return (layer, layer_source) where layer_source is `declared`, `inferred` or `unknown`."""
    if source_layer in LAYERS:
        return source_layer, "declared"
    for token in re.split(r"[^a-z0-9]+", table_name.casefold()):
        if token in _TOKEN_LAYER:
            return _TOKEN_LAYER[token], "inferred"
    default = _DEFAULT_BY_PLATFORM.get(platform)
    if default:
        return default, "inferred"
    return "unknown", "unknown"
