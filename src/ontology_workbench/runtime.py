from __future__ import annotations

import re

from ontology_workbench.models import utc_now_iso


STOP_WORDS = {"que", "como", "para", "con", "del", "las", "los", "una", "uno", "por", "sobre", "desde", "este", "esta", "son", "hay", "mas", "más", "the", "and"}


def select_fabric_query(question: str) -> str | None:
    """Route only unambiguous aggregate questions to the named Fabric gateway queries."""
    tokens = _tokens(question)
    if {"real", "default"}.issubset(tokens):
        return "impact_statuses"
    if ("nivel" in tokens or "niveles" in tokens) and ("riesgo" in tokens or "riesgos" in tokens):
        return "risk_levels"
    if ("cuantos" in tokens or "cuántos" in tokens or "total" in tokens) and ("riesgo" in tokens or "riesgos" in tokens):
        return "risk_summary"
    if "impacto" in tokens and ({"real", "default", "resumen"} & tokens):
        return "impact_summary"
    return None


def investigate_context_pack(context_pack: dict[str, object], question: str, investigation_id: str) -> dict[str, object]:
    _validate_query_contract(context_pack)
    tokens = _tokens(question)
    items = [
        {"item_type": item_type, **dict(item)}
        for item_type, key in (
            ("concept", "concepts"),
            ("business_rule", "business_rules"),
            ("kpi", "kpis"),
            ("property", "properties"),
            ("relationship", "relationships"),
            ("synonym", "synonyms"),
            ("constraint", "constraints"),
            ("technical_asset", "technical_assets"),
            ("source_binding", "data_bindings"),
        )
        for item in context_pack.get(key, [])
        if isinstance(item, dict)
    ]
    ranked = sorted(
        ((item, len(tokens.intersection(_tokens(f"{item.get('name', '')} {item.get('definition', '')}")))) for item in items),
        key=lambda pair: pair[1], reverse=True,
    )
    matches = [item for item, score in ranked if score > 0][:5]
    if not matches:
        answer = "Me abstengo: la release no contiene evidencia aprobada suficiente para responder esta pregunta."
        status = "abstained"
    else:
        labels = "; ".join(f"{item['name']}: {item['definition']}" for item in matches)
        answer = f"Segun la release consultada: {labels}"
        status = "answered"
    return {
        "manifest": {"format": "argos-investigation-v0.1", "investigation_id": investigation_id, "created_at": utc_now_iso(), "release_id": context_pack["release_id"], "status": status, "mode": "deterministic-context-pack"},
        "request": {"question": question},
        "retrieval": [{"item_id": item["id"], "item_type": item["item_type"], "name": item["name"], "definition": item["definition"], "source_binding": item.get("source_binding", item.get("linked_candidate_ids", []))} for item in matches],
        "answer": answer,
        "usage_boundary": context_pack["usage_boundary"],
    }


def _validate_query_contract(context_pack: dict[str, object]) -> None:
    query_contract = context_pack.get("query_contract")
    if not isinstance(query_contract, dict):
        raise ValueError("La release no contiene un contrato de consulta válido")
    allowed_operations = query_contract.get("allowed_operations")
    disallowed_operations = query_contract.get("disallowed_operations")
    if query_contract.get("requires_approved_data_binding") is not True:
        raise ValueError("Argos requiere source bindings aprobados")
    if allowed_operations != ["SELECT"] or not isinstance(disallowed_operations, list):
        raise ValueError("Argos solo permite consultas SELECT")
    if not any(operation in disallowed_operations for operation in ("INSERT", "UPDATE", "DELETE", "DDL")):
        raise ValueError("El contrato debe bloquear operaciones mutantes")


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-záéíóúñ0-9]+", value.casefold()) if len(token) > 2 and token not in STOP_WORDS}
