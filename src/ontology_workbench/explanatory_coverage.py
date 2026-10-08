from __future__ import annotations

import hashlib
import json
from copy import deepcopy

from ontology_workbench.explanatory_scope import ASPECTS


STATES = ("explained", "partial", "unexplained", "contradictory")
ASPECT_LABELS = {
    "significado": "significado", "granularidad": "granularidad", "identificacion": "identificacion",
    "extremos": "extremos de la relacion", "cardinalidad_si_aplica": "cardinalidad o no aplicabilidad",
    "definicion": "definicion", "formula": "formula", "filtros_y_exclusiones": "filtros y exclusiones",
    "tipo": "tipo", "valores_o_unidad": "valores o unidad",
}
DIAGNOSIS_MARKER = "\n\n## Cobertura explicativa y pedidos de informacion\n"


def compare_explanatory_assessments(before: dict, after: dict) -> dict:
    previous = before.get("explanatory_coverage", {})
    current = after.get("explanatory_coverage", {})
    if not previous or not current:
        return {"available": False, "reason": "Ambos assessments deben conservar una matriz explicativa."}
    old_rows = {row["element_id"]: row for row in previous["elements"]}
    new_rows = {row["element_id"]: row for row in current["elements"]}
    old_ids = {key for key, row in old_rows.items() if row["included"]}
    new_ids = {key for key, row in new_rows.items() if row["included"]}
    comparable = old_ids == new_ids and previous["scope_version"] == current["scope_version"]

    def evidence_signature(coverage, row):
        hashes = {chunk["chunk_id"]: chunk["text_hash"] for chunk in coverage.get("evidence_chunks", [])}
        return {(claim.get("aspect", "contradiction"), hashes.get(claim["chunk_id"], claim["quote"]), claim["quote"])
                for claim in row["evidence"] + row["contradictions"]}

    transitions = []
    for element_id in sorted(old_ids | new_ids):
        old = old_rows.get(element_id)
        new = new_rows.get(element_id)
        change = "added" if element_id not in old_rows else "included" if element_id not in old_ids else (
            "removed" if element_id not in new_rows else "excluded" if element_id not in new_ids else "unchanged")
        common = element_id in old_ids & new_ids
        new_evidence = evidence_signature(current, new) - evidence_signature(previous, old) if common else set()
        lost_evidence = evidence_signature(previous, old) - evidence_signature(current, new) if common else set()
        if common:
            if old["evaluation_status"] != "evaluated" and new["evaluation_status"] == "evaluated":
                change = "analysis_completed"
            elif old["state"] != new["state"] or old["evaluation_status"] != new["evaluation_status"]:
                change = "classification_changed"
            elif set(old["missing_aspects"]) != set(new["missing_aspects"]):
                change = "aspects_changed"
            elif new_evidence or lost_evidence:
                change = "evidence_changed"
        row = new or old
        transitions.append({"element_id": element_id, "name": row["name"], "kind": row["kind"], "change": change,
                            "before_state": old["state"] or old["evaluation_status"] if old else None,
                            "after_state": new["state"] or new["evaluation_status"] if new else None,
                            "missing_before": old["missing_aspects"] if old else [],
                            "missing_after": new["missing_aspects"] if new else [],
                            "new_evidence": [dict(aspect=aspect, text_hash=text_hash, quote=quote)
                                             for aspect, text_hash, quote in sorted(new_evidence)],
                            "lost_evidence_count": len(lost_evidence),
                            "reason": (new or old)["reason"]})
    outcomes = []
    for request in before.get("explanatory_diagnosis", {}).get("requests", []):
        new = new_rows.get(request["element_id"])
        outcome = "open"
        if request["element_id"] not in new_ids:
            outcome = "out_of_scope"
        elif new["evaluation_status"] == "evaluated":
            if request["action"] in ("evaluate", "retry_analysis"):
                outcome = "analysis_completed"
            elif new["state"] == "explained" or (request["action"] == "resolve_contradiction" and new["state"] != "contradictory"):
                outcome = "review_closure"
        outcomes.append({"request_id": request["request_id"], "element_name": request["element_name"],
                         "action": request["action"], "outcome": outcome, "closure_confirmed": False,
                         "after_state": (new["state"] or new["evaluation_status"]) if new else "removed",
                         "closure_criterion": request["closure_criterion"],
                         "current_request_ids": [item["request_id"] for item in after.get("explanatory_diagnosis", {}).get("requests", [])
                                                 if item["element_id"] == request["element_id"]]})
    groups = {}
    for kind in ASPECTS:
        old_group, new_group = previous["groups"][kind], current["groups"][kind]
        old_percent, new_percent = old_group["explained_percent"], new_group["explained_percent"]
        groups[kind] = {"before_denominator": old_group["denominator"], "after_denominator": new_group["denominator"],
                        "before_percent": old_percent, "after_percent": new_percent,
                        "delta_percentage_points": round(new_percent - old_percent, 2)
                        if comparable and old_percent is not None and new_percent is not None else None}
    return {"format": "atlas-explanatory-comparison-v1", "available": True,
            "before_run_id": before.get("manifest", {}).get("run_id"), "after_run_id": after.get("manifest", {}).get("run_id"),
            "before_scope_version": previous["scope_version"], "after_scope_version": current["scope_version"],
            "scope_changed": not comparable, "groups": groups, "transitions": transitions, "request_outcomes": outcomes,
            "limitations": list(dict.fromkeys(previous["limitations"] + current["limitations"])),
            "warning": "Cambios observados, no causalidad probada ni aprobacion. Los cierres requieren revision humana. "
                       "Las evidencias comparadas son las citadas; duplicar texto no agrega respaldo."}


def build_explanatory_diagnosis(coverage: dict, scope_definition: dict, source_inventory: dict) -> dict:
    if not coverage:
        return {}
    rows = [row for row in coverage["elements"] if row["included"]]
    sources = {source["source_id"]: source for source in source_inventory.get("technical_sources", [])}
    cases = {case["use_case_id"]: case for case in scope_definition.get("use_cases", [])}

    def summarize(selected):
        groups = {}
        for kind in ASPECTS:
            elements = [row for row in selected if row["kind"] == kind]
            counts = {state: sum(row["state"] == state for row in elements) for state in STATES}
            evaluated = sum(counts.values())
            groups[kind] = {"denominator": len(elements), "evaluated": evaluated, "counts": counts,
                            "explained_percent": round(100 * counts["explained"] / len(elements), 2)
                            if elements and evaluated else None,
                            "failed": sum(row["evaluation_status"] == "failed" for row in elements),
                            "not_evaluated": sum(row["evaluation_status"] == "not_evaluated" for row in elements)}
        return groups

    systems = [{"source_id": source_id, "name": source.get("name", source_id),
                "groups": summarize([row for row in rows if source_id in row["source_ids"]])}
               for source_id, source in sources.items()]
    if any(not row["source_ids"] or "" in row["source_ids"] for row in rows):
        systems.append({"source_id": "", "name": "Sin sistema identificado",
                        "groups": summarize([row for row in rows if not row["source_ids"] or "" in row["source_ids"]])})
    use_cases = [{"use_case_id": case_id, "name": case.get("name", case_id), "link_basis": "source_scope_only",
                  "groups": summarize([row for row in rows if case_id in row["use_case_ids"]])}
                 for case_id, case in cases.items()]
    requests = []
    for row in rows:
        if row["state"] == "explained":
            continue
        owners = sorted({sources[source_id].get("owner", "").strip() for source_id in row["source_ids"]
                         if source_id in sources and sources[source_id].get("owner", "").strip()})
        case_owners = sorted({cases[case_id].get("owner", "").strip() for case_id in row["use_case_ids"]
                              if case_id in cases and cases[case_id].get("owner", "").strip()})
        owner = ", ".join(owners or case_owners) or scope_definition.get("domain_owner") or "Por confirmar"
        if row["evaluation_status"] in ("failed", "not_evaluated"):
            action = "retry_analysis" if row["evaluation_status"] == "failed" else "evaluate"
            required = "Reintentar el analisis y revisar el error registrado." if action == "retry_analysis" else "Completar el contraste de la evidencia disponible."
            closure = "Una evaluacion completa y trazable clasifica el elemento; no basta adjuntar otro documento."
        elif row["state"] == "contradictory":
            action = "resolve_contradiction"
            required = "Confirmar la definicion aplicable y resolver las contradicciones documentadas."
            closure = "Una fuente autorizada explica la definicion aplicable; al reevaluar no queda contradiccion material pendiente."
        else:
            action = "request_evidence"
            aspects = ", ".join(ASPECT_LABELS.get(aspect, aspect) for aspect in row["missing_aspects"])
            required = f"Solicitar documentacion que explique: {aspects}."
            closure = "La nueva evidencia respalda los aspectos faltantes con citas verificables y permite reevaluar el elemento."
        priority = "alta" if action in ("retry_analysis", "resolve_contradiction") or any(
            cases.get(case_id, {}).get("priority") == "alta" for case_id in row["use_case_ids"]) else "media"
        requests.append({"request_id": f"request-{row['element_id']}-{action}", "element_id": row["element_id"],
                         "element_name": row["name"], "kind": row["kind"], "action": action,
                         "request": f"{row['name']}: {required}", "required_information": required,
                         "proposed_owner": owner, "owner_confirmed": False, "priority": priority,
                         "closure_criterion": closure, "status": "open", "reason": row["reason"],
                         "missing_aspects": row["missing_aspects"] if action == "request_evidence" else [],
                         "source_ids": row["source_ids"], "use_case_ids": row["use_case_ids"],
                         "evidence": row["evidence"], "contradictions": row["contradictions"]})
    requests.sort(key=lambda item: (item["priority"] != "alta", item["element_name"], item["request_id"]))
    return {"format": "atlas-explanatory-diagnosis-v1", "scope_version": coverage["scope_version"],
            "systems": systems, "use_cases": use_cases, "requests": requests,
            "limitations": coverage["limitations"],
            "use_case_link_warning": "Los casos de uso se vinculan por sistema, no por relevancia semantica confirmada."}


def attach_explanatory_diagnosis(package: dict) -> None:
    coverage = package.get("explanatory_coverage", {})
    if not coverage:
        return
    diagnosis = build_explanatory_diagnosis(coverage, package.get("scope_definition", {}), package.get("source_inventory", {}))
    package["explanatory_diagnosis"] = diagnosis
    artifacts = package["manifest"]["artifacts"]
    if "explanatory_diagnosis.json" not in artifacts:
        artifacts.append("explanatory_diagnosis.json")
    lines = ["Cobertura del inventario disponible. Explicado no significa aprobado.", diagnosis["use_case_link_warning"]]
    for kind, group in coverage["groups"].items():
        percent = group["explained_percent"]
        value = "No evaluable" if not group["denominator"] else "Sin evaluar" if percent is None else f"{percent:g}%"
        lines.append(f"- {kind}: {value}; {group['counts']['explained']} explicados / {group['denominator']} en alcance; "
                     f"{group['evaluated']} evaluados; {group['failed']} fallos.")
    lines.extend(f"- Limite: {limitation}" for limitation in diagnosis["limitations"])
    for dimension, entries in (("Sistema", diagnosis["systems"]), ("Caso de uso por sistema", diagnosis["use_cases"])):
        for entry in entries:
            lines.append(f"\n### {dimension}: {entry['name']}\n")
            for kind, group in entry["groups"].items():
                percent = group["explained_percent"]
                value = "No evaluable" if not group["denominator"] else "Sin evaluar" if percent is None else f"{percent:g}%"
                lines.append(f"- {kind}: {value}; {group['counts']['explained']} / {group['denominator']} en alcance.")
    lines.append("\n### Pedidos abiertos\n")
    for request in diagnosis["requests"]:
        lines.extend([f"- {request['request_id']}: {request['request']}",
                      f"  Responsable propuesto: {request['proposed_owner']}; prioridad: {request['priority']}.",
                      f"  Cierre: {request['closure_criterion']}"])
    if not diagnosis["requests"]:
        lines.append("Sin pedidos abiertos derivados de esta matriz.")
    package["execution_summary"] = str(package.get("execution_summary", "")).split(DIAGNOSIS_MARKER)[0] + DIAGNOSIS_MARKER + "\n".join(lines) + "\n"


def build_explanatory_coverage(scope: dict, chunks: list[dict], evaluations: list[dict] | None = None) -> dict:
    evidence = {}
    versions = {}
    ambiguous_ids = set()
    for chunk in chunks:
        chunk_id = chunk["chunk_id"]
        if chunk_id not in evidence:
            evidence[chunk_id] = chunk
            versions[chunk_id] = [chunk]
        elif evidence[chunk_id]["text"] != chunk["text"]:
            ambiguous_ids.add(chunk_id)
            if not any(version["text"] == chunk["text"] for version in versions[chunk_id]):
                versions[chunk_id].append(chunk)
    elements = {item["element_id"]: item for item in scope["elements"]}
    decisions = {}
    for evaluation in evaluations or []:
        element_id = evaluation.get("element_id")
        if element_id not in elements:
            raise ValueError("La clasificacion referencia un elemento fuera del universo.")
        if element_id in decisions and decisions[element_id] != evaluation:
            raise ValueError("Las clasificaciones del mismo elemento requieren consolidacion.")
        decisions[element_id] = evaluation
    rows = []
    cited_ids = set()
    for item in scope["elements"]:
        row = deepcopy(item)
        row.update(state=None, method=None, reason="Sin clasificacion estructurada.", supported_aspects=[],
                   missing_aspects=list(item["required_aspects"]), evidence=[], contradictions=[],
                   validation_errors=[], evaluation_status="not_evaluated")
        decision = decisions.get(item["element_id"])
        if not item["included"]:
            row.update(evaluation_status="excluded", reason=item["scope_reason"])
        elif decision is not None:
            method = decision.get("method")
            row["method"] = method
            errors = row["validation_errors"]
            if not isinstance(method, str) or not method.strip():
                errors.append("Falta el metodo de evaluacion.")
            if decision.get("evaluation_status", "evaluated") != "evaluated":
                errors.append("La evaluacion no se completo.")
            for field in ("supports", "contradictions"):
                claims = decision.get(field, [])
                if not isinstance(claims, list):
                    errors.append(f"{field}: se requiere una lista.")
                    continue
                seen = set()
                for claim in claims:
                    if not isinstance(claim, dict):
                        errors.append(f"{field}: evidencia invalida.")
                        continue
                    chunk = evidence.get(claim.get("chunk_id"))
                    if claim.get("chunk_id") in ambiguous_ids:
                        errors.append("ID de fragmento ambiguo: no puede respaldar la clasificacion.")
                        continue
                    if chunk is not None:
                        cited_ids.add(claim["chunk_id"])
                    quote = claim.get("quote")
                    if chunk is None or not isinstance(quote, str) or not quote.strip() or quote not in chunk["text"]:
                        errors.append(f"{field}: fragmento inexistente o cita no respaldada por el texto.")
                        continue
                    if field == "supports" and claim.get("aspect") not in item["required_aspects"]:
                        errors.append("Aspecto fuera de los requisitos del elemento.")
                        continue
                    if field == "contradictions" and (
                        not isinstance(claim.get("material", True), bool)
                        or not isinstance(claim.get("resolved", False), bool)
                        or not str(claim.get("reason", "")).strip()
                    ):
                        errors.append("Contradiccion sin motivo o indicadores invalidos.")
                        continue
                    fingerprint = json.dumps(claim, sort_keys=True)
                    if fingerprint in seen:
                        continue
                    seen.add(fingerprint)
                    citation = deepcopy(claim)
                    citation.update(document_id=chunk.get("document_id"), filename=chunk.get("filename"))
                    row["evidence" if field == "supports" else "contradictions"].append(citation)
                    cited_ids.add(claim["chunk_id"])
            supported = {citation["aspect"] for citation in row["evidence"]}
            row["supported_aspects"] = sorted(supported)
            row["missing_aspects"] = [aspect for aspect in item["required_aspects"] if aspect not in supported]
            if errors:
                row.update(evaluation_status="failed", reason="; ".join(dict.fromkeys(errors)))
            else:
                material = any(claim.get("material", True) and not claim.get("resolved", False)
                               for claim in row["contradictions"])
                state = "contradictory" if material else (
                    "explained" if not row["missing_aspects"] else "partial" if supported else "unexplained")
                row.update(state=state, evaluation_status="evaluated",
                           reason=decision.get("reason") or f"Clasificacion estructurada: {state}.")
        rows.append(row)
    groups = {}
    for kind in ASPECTS:
        included = [row for row in rows if row["kind"] == kind and row["included"]]
        total = len(included)
        counts = {state: sum(row["state"] == state for row in included) for state in STATES}
        evaluated = sum(counts.values())
        groups[kind] = {
            "denominator": total, "evaluated": evaluated, "counts": counts,
            "not_evaluated": sum(row["evaluation_status"] == "not_evaluated" for row in included),
            "failed": sum(row["evaluation_status"] == "failed" for row in included),
            "explained_percent": round(100 * counts["explained"] / total, 2) if total and evaluated else None,
            "state_percentages": {state: round(100 * count / total, 2) if total and evaluated else None
                                  for state, count in counts.items()},
            "processing_percent": round(100 * evaluated / total, 2) if total else None,
        }
    limitations = list(scope["limitations"])
    if ambiguous_ids:
        limitations.append("Hay IDs de fragmentos ambiguos; sus referencias no respaldan clasificaciones.")
    if any(group["evaluated"] < group["denominator"] for group in groups.values()):
        limitations.append("Hay elementos sin evaluar o con fallos; no demuestran ausencia de explicacion.")
    snapshots = []
    for chunk_id in sorted(cited_ids | ambiguous_ids):
        for version in versions[chunk_id]:
            chunk = deepcopy(version)
            chunk["text_hash"] = hashlib.sha256(chunk["text"].encode()).hexdigest()
            snapshots.append(chunk)
    return {
        "format": "atlas-explanatory-coverage-v1", "scope_version": scope["scope_version"],
        "criteria_version": scope["criteria_version"], "calculation_version": "coverage-counts-v1",
        "method": "structured_evidence", "elements": rows, "groups": groups,
        "evaluation_inputs": [deepcopy(decisions[element_id]) for element_id in sorted(decisions)],
        "ambiguous_chunk_ids": sorted(ambiguous_ids),
        "evidence_chunks": snapshots, "limitations": limitations,
        "validation_boundary": "Valida IDs, citas y requisitos; no valida automaticamente el respaldo semantico ni aprueba conocimiento.",
    }