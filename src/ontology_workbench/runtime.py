from __future__ import annotations

import re
import json

from ontology_workbench.context_scanner import LlmSettings, call_llm_json
from ontology_workbench.models import utc_now_iso


STOP_WORDS = {"que", "como", "para", "con", "del", "las", "los", "una", "uno", "por", "sobre", "desde", "este", "esta", "son", "hay", "mas", "más", "the", "and"}


def select_fabric_query(question: str) -> str | None:
    """Route only unambiguous aggregate questions to the named Fabric gateway queries."""
    tokens = _tokens(question)
    if _risk_rule_sic_parameters(question) is not None and (
        {"riesgo", "valor", "nivel"} & tokens
    ):
        return "risk_rule_sic"
    if _sic_parameter(question) is not None and {"riesgo", "riesgos"} & tokens:
        return "risk_sic"
    if {"real", "default"}.issubset(tokens):
        return "impact_statuses"
    if ("nivel" in tokens or "niveles" in tokens) and ("riesgo" in tokens or "riesgos" in tokens):
        return "risk_levels"
    if ("cuantos" in tokens or "cuántos" in tokens or "total" in tokens) and ("riesgo" in tokens or "riesgos" in tokens):
        return "risk_summary"
    if "impacto" in tokens and ({"real", "default", "resumen"} & tokens):
        return "impact_summary"
    return None


def fabric_query_parameters(question: str) -> tuple[int, int] | None:
    """Extract only the bounded parameters for the named rule/SIC query."""
    return _risk_rule_sic_parameters(question)


def sic_query_parameter(question: str) -> int | None:
    return _sic_parameter(question)


def _risk_rule_sic_parameters(question: str) -> tuple[int, int] | None:
    normalized_question = question.casefold()
    rule_match = re.search(r"\b(?:regla|riesgo)\s*(\d+)\b", normalized_question)
    sic_match = re.search(r"\bsic\s*(\d+)\b", question.casefold())
    if not sic_match:
        sic_match = re.search(r"\ben\s+el\s+(?:sic\s*)?(\d+)\b", normalized_question)
    if not rule_match or not sic_match:
        return None
    return int(rule_match.group(1)), int(sic_match.group(1))


def _sic_parameter(question: str) -> int | None:
    match = re.search(r"\bsic\s*(\d+)\b", question.casefold())
    return int(match.group(1)) if match else None


def investigate_context_pack(context_pack: dict[str, object], question: str, investigation_id: str) -> dict[str, object]:
    _validate_query_contract(context_pack)
    matches = _rank_context_matches(context_pack, question)
    if not matches:
        answer = "Me abstengo: la release no contiene evidencia aprobada suficiente para responder esta pregunta."
        status = "abstained"
    else:
        labels = "; ".join(
            f"{item.get('name', 'sin nombre')}: {item.get('definition', 'sin definicion')}"
            for item in matches
        )
        answer = f"Segun la release consultada: {labels}"
        status = "answered"
    visualization = _build_mermaid_visualization(context_pack, matches, question)
    return {
        "manifest": {"format": "argos-investigation-v0.1", "investigation_id": investigation_id, "created_at": utc_now_iso(), "release_id": context_pack["release_id"], "status": status, "mode": "deterministic-context-pack"},
        "request": {"question": question},
        "retrieval": [
            {
                "item_id": item.get("id", ""),
                "item_type": item.get("item_type", "unknown"),
                "name": item.get("name", "sin nombre"),
                "definition": item.get("definition", "sin definicion"),
                "source_binding": item.get("source_binding", item.get("linked_candidate_ids", [])),
            }
            for item in matches
        ],
        "answer": answer,
        "interpretation": _build_interpretation(matches, status),
        "visualization": visualization,
        "usage_boundary": context_pack["usage_boundary"],
    }


def investigate_context_pack_with_llm(
    context_pack: dict[str, object],
    question: str,
    investigation_id: str,
    settings: LlmSettings,
    query_catalog: dict[str, dict[str, object]],
    live_query_runner,
) -> dict[str, object]:
    """Let the configured model plan and explain an investigation over approved context."""
    _validate_query_contract(context_pack)
    matches = _rank_context_matches(context_pack, question)
    context_json = json.dumps(context_pack, ensure_ascii=False, separators=(",", ":"))
    catalog_json = json.dumps(query_catalog, ensure_ascii=False, separators=(",", ":"))
    plan = call_llm_json(
        [
            {
                "role": "system",
                "content": (
                    "Eres Argos, un analista senior de negocio. Decide como investigar usando "
                    "exclusivamente el contexto aprobado. No inventes definiciones ni datos. "
                    "Puedes elegir una consulta del catalogo, o ninguna. Nunca escribas SQL. "
                    "Devuelve solo JSON con query_name (string o null), parameters (objeto), "
                    "needs_stronger_model (boolean) y reasoning_note (string)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Pregunta del negocio:\n{question}\n\n"
                    f"Catalogo de capacidades y consultas permitidas:\n{catalog_json}\n\n"
                    f"Contexto aprobado de Atlas/Nexo:\n{context_json}"
                ),
            },
        ],
        settings,
    )
    query_name = plan.get("query_name")
    if query_name is not None and str(query_name) not in query_catalog:
        query_name = None
    query_result = None
    if query_name:
        parameters = plan.get("parameters", {})
        query_result = live_query_runner(str(query_name), parameters)
    evidence = {
        "context_pack": context_pack,
        "live_query": query_result or {},
        "llm_plan": plan,
    }
    answer = call_llm_json(
        [
            {
                "role": "system",
                "content": (
                    "Eres Argos. Responde en español a un usuario de negocio con claridad y criterio. "
                    "Usa solo la evidencia entregada. Si falta evidencia, dilo. No menciones SQL ni "
                    "nombres internos salvo que ayuden a un analista. Devuelve solo JSON con answer, "
                    "interpretation, suggested_questions (lista de strings), visualization (objeto "
                    "con title y description o null), needs_stronger_model (boolean) y reasoning_note."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Pregunta:\n{question}\n\nEvidencia disponible:\n"
                    f"{json.dumps(evidence, ensure_ascii=False, separators=(',', ':'))}"
                ),
            },
        ],
        settings,
    )
    has_live_evidence = bool(query_result and query_result.get("rows"))
    has_context_evidence = bool(matches)
    status = "answered" if (has_live_evidence or has_context_evidence) and str(answer.get("answer", "")).strip() else "abstained"
    if status == "abstained":
        answer["answer"] = "Me abstengo: la release no contiene evidencia aprobada suficiente para responder esta pregunta."
    return {
        "manifest": {
            "format": "argos-investigation-v0.2",
            "investigation_id": investigation_id,
            "created_at": utc_now_iso(),
            "release_id": context_pack["release_id"],
            "status": status,
            "mode": "llm-context-pack-plus-fabric-read-only" if query_result else "llm-context-pack",
        },
        "request": {"question": question},
        "retrieval": [
            {
                "item_id": item.get("id", ""),
                "item_type": item.get("item_type", "unknown"),
                "name": item.get("name", "sin nombre"),
                "definition": item.get("definition", "sin definicion"),
                "source_binding": item.get("source_binding", item.get("linked_candidate_ids", [])),
            }
            for item in matches
        ],
        "answer": str(answer.get("answer", "Me abstengo: el modelo no pudo construir una respuesta sustentada.")),
        "interpretation": str(answer.get("interpretation", "")),
        "suggested_questions": [str(item) for item in answer.get("suggested_questions", []) if str(item).strip()],
        "visualization": answer.get("visualization"),
        "live_query": query_result,
        "llm_plan": plan,
        "llm_response": answer,
        "usage_boundary": context_pack["usage_boundary"],
    }


def _rank_context_matches(context_pack: dict[str, object], question: str) -> list[dict[str, object]]:
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
        (
            (item, len(tokens.intersection(_tokens(f"{item.get('name', '')} {item.get('definition', '')}"))))
            for item in items
        ),
        key=lambda pair: pair[1],
        reverse=True,
    )
    return [item for item, score in ranked if score > 0][:5]


def _build_interpretation(matches: list[dict[str, object]], status: str) -> str:
    if status != "answered":
        return "No hay evidencia aprobada suficiente para construir una interpretacion."
    if not matches:
        return "La respuesta se basa en evidencia aprobada de la release, sin inferir datos fuera de ella."
    return (
        f"La interpretacion se basa en {len(matches)} elemento(s) aprobado(s) de la release. "
        "Debe distinguirse entre definiciones documentadas y conclusiones que requieren mas evidencia."
    )


def _build_mermaid_visualization(
    context_pack: dict[str, object], matches: list[dict[str, object]], question: str
) -> dict[str, str] | None:
    normalized = question.casefold()
    if not any(term in normalized for term in ("mermaid", "diagrama", "grafico", "gráfico", "relacion", "relación")):
        return None
    matched_ids = {str(item.get("id", "")) for item in matches}
    nodes = [
        item for item in context_pack.get("concepts", [])
        if isinstance(item, dict) and str(item.get("id", "")) in matched_ids
    ]
    node_ids = {str(item.get("id", "")): f"n{index}" for index, item in enumerate(nodes, start=1)}
    lines = ["graph TD"]
    for item in nodes:
        node_id = node_ids[str(item["id"])]
        lines.append(f"    {node_id}[\"{_mermaid_text(item.get('name', 'concepto'))}\"]")
    for relation in context_pack.get("relationships", []):
        if not isinstance(relation, dict):
            continue
        source = str(relation.get("source_id", ""))
        target = str(relation.get("target_id", ""))
        if source in node_ids and target in node_ids:
            label = _mermaid_text(relation.get("name", relation.get("relation_type", "relaciona")))
            lines.append(f"    {node_ids[source]} -->|{label}| {node_ids[target]}")
    if len(lines) == 1:
        return {
            "type": "mermaid",
            "status": "insufficient_evidence",
            "code": "graph TD\n    A[Sin relaciones aprobadas suficientes]",
        }
    return {"type": "mermaid", "status": "generated_from_release", "code": "\n".join(lines)}


def _mermaid_text(value: object) -> str:
    return str(value).replace('"', "'").replace("|", "/").replace("\n", " ")[:120]


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
