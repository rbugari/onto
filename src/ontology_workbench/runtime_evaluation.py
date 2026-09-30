from __future__ import annotations

from collections.abc import Callable

from ontology_workbench.models import utc_now_iso
from ontology_workbench.runtime import investigate_context_pack


def suggest_evaluation_cases(context_pack: dict[str, object]) -> list[dict[str, str]]:
    """Create a small, editable baseline that exercises both answer and abstention paths."""
    generic_names = {"tipo", "real", "default", "constante", "valor", "estado"}
    available_items = [
        item
        for key in ("concepts", "business_rules", "kpis", "properties", "relationships", "synonyms", "constraints")
        for item in context_pack.get(key, [])
        if (
            isinstance(item, dict)
            and str(item.get("name", "")).strip()
            and str(item.get("name", "")).strip().casefold() not in generic_names
            and len(str(item.get("name", "")).strip()) >= 5
        )
    ]
    cases = [
        {
            "case_id": f"answer-{index:02d}",
            "question": f"¿Qué es {item['name']}?",
            "expected_status": "answered",
            "expected_item_name": str(item["name"]),
        }
        for index, item in enumerate(available_items[:5], start=1)
    ]
    cases.append(
        {
            "case_id": "abstention-01",
            "question": "¿Qué planeta es más grande?",
            "expected_status": "abstained",
            "expected_item_name": "",
        }
    )
    has_risk_table = any(
        "gold_sic.fact_riesgo" in str(item.get("name", ""))
        for key in ("technical_assets", "data_bindings")
        for item in context_pack.get(key, [])
        if isinstance(item, dict)
    )
    if has_risk_table:
        cases.insert(
            0,
            {
                "case_id": "business-risk-rule-sic-01",
                "question": "¿Cuál es el riesgo de la regla 1003 en el SIC12?",
                "expected_status": "answered",
                "expected_item_name": "",
            },
        )
    return cases


def evaluate_context_pack(
    context_pack: dict[str, object],
    cases: list[dict[str, object]],
    evaluation_id: str,
    investigator: Callable[[str, str], dict[str, object]] | None = None,
) -> dict[str, object]:
    results: list[dict[str, object]] = []
    for index, case in enumerate(cases, start=1):
        question = str(case.get("question", "")).strip()
        expected_status = str(case.get("expected_status", "")).strip()
        expected_item_name = str(case.get("expected_item_name", "")).strip()
        if not question or expected_status not in {"answered", "abstained"}:
            raise ValueError("Cada caso requiere una pregunta y expected_status answered o abstained")
        investigation = (
            investigator(question, f"{evaluation_id}-case-{index:03d}")
            if investigator
            else investigate_context_pack(context_pack, question, f"{evaluation_id}-case-{index:03d}")
        )
        retrieved_names = [str(item["name"]) for item in investigation["retrieval"]]
        status_match = investigation["manifest"]["status"] == expected_status
        evidence_match = not expected_item_name or expected_item_name in retrieved_names
        results.append(
            {
                "case_id": str(case.get("case_id", f"case-{index:03d}")),
                "question": question,
                "expected_status": expected_status,
                "expected_item_name": expected_item_name,
                "actual_status": investigation["manifest"]["status"],
                "retrieved_item_names": retrieved_names,
                "passed": status_match and evidence_match,
                "failure_reason": _failure_reason(status_match, evidence_match),
                "investigation": investigation,
            }
        )
    passed = sum(1 for result in results if result["passed"])
    return {
        "manifest": {
            "format": "argos-evaluation-v0.1",
            "evaluation_id": evaluation_id,
            "created_at": utc_now_iso(),
            "release_id": context_pack["release_id"],
            "mode": "deterministic-context-pack",
        },
        "summary": {"total": len(results), "passed": passed, "failed": len(results) - passed},
        "cases": results,
    }


def _failure_reason(status_match: bool, evidence_match: bool) -> str:
    if not status_match:
        return "El estado de respuesta no coincide con lo esperado."
    if not evidence_match:
        return "La respuesta no recuperó el elemento de evidencia esperado."
    return ""


def parse_evaluation_cases(text: str) -> tuple[list[dict[str, str]], list[str]]:
    """Parse `question | answered|abstained | expected evidence` lines; returns cases and invalid line numbers."""
    cases: list[dict[str, str]] = []
    invalid: list[str] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip():
            continue
        values = [value.strip() for value in raw_line.split("|", maxsplit=2)]
        if not values[0] or (len(values) >= 2 and values[1] not in {"answered", "abstained"}):
            invalid.append(str(line_number))
            continue
        cases.append(
            {
                "case_id": f"manual-{line_number:03d}",
                "question": values[0],
                "expected_status": values[1] if len(values) > 1 else "answered",
                "expected_item_name": values[2] if len(values) > 2 else "",
            }
        )
    return cases, invalid
