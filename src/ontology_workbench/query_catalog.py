from __future__ import annotations

import re
from copy import deepcopy


QUERY_CATALOG_FORMAT = "onto-query-catalog-v0.1"

LEGACY_FABRIC_QUERY_CATALOG: list[dict[str, object]] = [
    {
        "query_name": "risk_rule_sic",
        "description": "Consultar el riesgo mas reciente de una regla en un SIC.",
        "example_question": "¿Cuál es el riesgo de la regla 1 en el SIC 12?",
        "visualization": {
            "type": "metrics",
            "fields": ["probabilidad_final_texto", "impacto_final_texto", "riesgo_final_texto", "metodo_calculo"],
        },
        "adapter": "fabric",
        "template_id": "risk_rule_sic",
        "binding_required": "gold_sic.fact_riesgo",
        "allowed_parameters": ["id_risc", "sic"],
        "max_rows": 1,
        "routing": {"any_terms": ["riesgo", "valor", "nivel", "regla"]},
        "parameter_extractors": {
            "id_risc": {
                "type": "integer",
                "patterns": [r"\b(?:regla|riesgo)\s*(\d+)\b"],
            },
            "sic": {
                "type": "integer",
                "patterns": [r"\bsic\s*(\d+)\b", r"\ben\s+el\s+(?:sic\s*)?(\d+)\b"],
            },
        },
    },
    {
        "query_name": "risk_sic",
        "description": "Listar los riesgos de un SIC.",
        "adapter": "fabric",
        "template_id": "risk_sic",
        "binding_required": "gold_sic.fact_riesgo",
        "allowed_parameters": ["sic"],
        "max_rows": 100,
        "routing": {"any_terms": ["riesgo", "riesgos"], "requires_parameter": "sic"},
        "parameter_extractors": {
            "sic": {
                "type": "integer",
                "patterns": [r"\bsic\s*(\d+)\b", r"\ben\s+el\s+(?:sic\s*)?(\d+)\b"],
            }
        },
    },
    {
        "query_name": "risk_levels",
        "description": "Distribuir los riesgos por nivel final.",
        "example_question": "¿Cómo se distribuyen los riesgos por nivel?",
        "visualization": {"type": "bar", "x": "riesgo_final_texto", "y": "total_rows"},
        "adapter": "fabric",
        "template_id": "risk_levels",
        "binding_required": "gold_sic.fact_riesgo",
        "allowed_parameters": [],
        "max_rows": 10,
        "routing": {"all_terms": ["riesgo"], "any_terms": ["nivel", "niveles"]},
    },
    {
        "query_name": "risk_summary",
        "description": "Contar registros de riesgo y SIC distintos.",
        "adapter": "fabric",
        "template_id": "risk_summary",
        "binding_required": "gold_sic.fact_riesgo",
        "allowed_parameters": [],
        "max_rows": 1,
        "routing": {"any_terms": ["riesgo", "riesgos"], "any_question_terms": ["cuantos", "total"]},
    },
    {
        "query_name": "impact_statuses",
        "description": "Comparar estados REAL y DEFAULT de impactos.",
        "adapter": "fabric",
        "template_id": "impact_statuses",
        "binding_required": "gold_sic.fact_impacto",
        "allowed_parameters": [],
        "max_rows": 10,
        "routing": {"all_terms": ["real", "default"]},
    },
    {
        "query_name": "impact_summary",
        "description": "Resumir valores de impacto.",
        "adapter": "fabric",
        "template_id": "impact_summary",
        "binding_required": "gold_sic.fact_impacto_bloque",
        "allowed_parameters": [],
        "max_rows": 1,
        "routing": {"all_terms": ["impacto"], "any_terms": ["real", "default", "resumen"]},
    },
]


def normalize_query_catalog(raw_catalog: object) -> dict[str, dict[str, object]]:
    if raw_catalog is None:
        return {}
    if isinstance(raw_catalog, dict):
        entries = raw_catalog.get("queries")
        if entries is None and all(isinstance(value, dict) for value in raw_catalog.values()):
            entries = list(raw_catalog.values())
        if entries is None:
            entries = []
    else:
        entries = raw_catalog
    if not isinstance(entries, list):
        raise ValueError("query_catalog debe ser una lista de consultas")
    normalized: dict[str, dict[str, object]] = {}
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            raise ValueError("Cada entrada de query_catalog debe ser un objeto")
        name = str(raw_entry.get("query_name", raw_entry.get("name", ""))).strip()
        if not name or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            raise ValueError("Cada consulta necesita un query_name seguro")
        entry = deepcopy(raw_entry)
        entry["query_name"] = name
        entry.setdefault("adapter", "fabric")
        entry.setdefault("template_id", name)
        entry.setdefault("allowed_parameters", [])
        entry.setdefault("max_rows", 100)
        adapter = str(entry["adapter"]).casefold()
        if adapter == "mariadb":
            connection_profile = str(entry.get("connection_profile", "")).strip()
            if not connection_profile or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", connection_profile):
                raise ValueError(f"connection_profile invalido para {name}")
            entry["connection_profile"] = connection_profile
        if not isinstance(entry["allowed_parameters"], list):
            raise ValueError(f"allowed_parameters invalido para {name}")
        entry["allowed_parameters"] = [str(item) for item in entry["allowed_parameters"]]
        if not isinstance(entry["max_rows"], int) or not 1 <= entry["max_rows"] <= 10_000:
            raise ValueError(f"max_rows invalido para {name}")
        for parameter_name, extractor in dict(entry.get("parameter_extractors", {})).items():
            if not isinstance(extractor, dict):
                raise ValueError(f"Extractor invalido para {name}.{parameter_name}")
            for pattern in extractor.get("patterns", []):
                re.compile(str(pattern))
        normalized[name] = entry
    return normalized


def catalog_for_context(context_pack: dict[str, object]) -> dict[str, dict[str, object]]:
    configured = normalize_query_catalog(context_pack.get("query_catalog"))
    if context_pack.get("query_catalog_configured", "query_catalog" in context_pack):
        return configured
    return normalize_query_catalog(LEGACY_FABRIC_QUERY_CATALOG)


def select_catalog_query(
    question: str, catalog: dict[str, dict[str, object]]
) -> str | None:
    tokens = _tokens(question)
    for name, specification in catalog.items():
        routing = specification.get("routing", {})
        if not isinstance(routing, dict):
            continue
        all_terms = {str(item).casefold() for item in routing.get("all_terms", [])}
        any_terms = {str(item).casefold() for item in routing.get("any_terms", [])}
        any_question_terms = {
            str(item).casefold() for item in routing.get("any_question_terms", [])
        }
        if all_terms and not all_terms.issubset(tokens):
            continue
        if any_terms and not any_terms.intersection(tokens):
            continue
        if any_question_terms and not any_question_terms.intersection(tokens):
            continue
        parameters = extract_query_parameters(question, specification)
        required_parameter = routing.get("requires_parameter")
        if required_parameter and required_parameter not in parameters:
            continue
        if any(
            parameter_name not in parameters
            for parameter_name in specification.get("allowed_parameters", [])
        ):
            continue
        return name
    return None


def extract_query_parameters(
    question: str, specification: dict[str, object]
) -> dict[str, int | str]:
    result: dict[str, int | str] = {}
    extractors = specification.get("parameter_extractors", {})
    if not isinstance(extractors, dict):
        return result
    for parameter_name in specification.get("allowed_parameters", []):
        extractor = extractors.get(parameter_name)
        if not isinstance(extractor, dict):
            continue
        for pattern in extractor.get("patterns", []):
            match = re.search(str(pattern), question.casefold())
            if not match:
                continue
            value = match.group(1)
            result[str(parameter_name)] = int(value) if extractor.get("type") == "integer" else value
            break
    return result


def ordered_query_parameters(
    specification: dict[str, object], parameters: object
) -> tuple[int | str, ...]:
    if parameters is None:
        parameters = {}
    if not isinstance(parameters, dict):
        raise ValueError("Los parametros de una consulta deben ser un objeto")
    allowed = [str(item) for item in specification.get("allowed_parameters", [])]
    unknown = set(parameters) - set(allowed)
    if unknown:
        raise ValueError("La consulta contiene parametros no permitidos")
    missing = [name for name in allowed if name not in parameters]
    if missing:
        raise ValueError("Faltan parametros requeridos de la consulta")
    return tuple(parameters[name] for name in allowed)


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-záéíóúñ0-9]+", value.casefold()))