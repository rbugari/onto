from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import unicodedata


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def _identities(draft: dict) -> dict[str, str]:
    candidates = {item["candidate_id"]: item for item in draft["candidates"]}
    identities = {identifier: item.get("identity_key") or _digest([
        item["candidate_type"], _normalize(item["name"]), item.get("source_id", "")])
        for identifier, item in candidates.items() if not item.get("change_of")}
    for identifier, item in candidates.items():
        if not item.get("change_of") and item.get("linked_candidate_ids") and not item.get("identity_key"):
            identities[identifier] = _digest([item["candidate_type"], _normalize(item["name"]),
                sorted(identities.get(link, link) for link in item["linked_candidate_ids"])])
    for item in draft.get("model_elements", []):
        if not item.get("change_of"):
            identities[item["element_id"]] = item.get("identity_key") or _digest([
                item["element_type"], _normalize(item["name"]),
                [identities.get(link, link) for link in item.get("linked_candidate_ids", [])]])
    return identities


def _material(item: dict, identities: dict, references: dict, candidates: dict) -> str:
    sources = {reference: references.get(reference) for reference in item.get("source_refs", [])}
    return _digest({"name": _normalize(item["name"]), "definition": item.get("definition", ""),
        "owner": item.get("owner", ""), "validation_needed": item.get("validation_needed", ""),
        "links": [identities.get(link, link) for link in item.get("linked_candidate_ids", [])],
        "dependencies": [{"name": candidates[link]["name"], "definition": candidates[link].get("definition", ""),
                  "sources": {ref: references.get(ref) for ref in candidates[link].get("source_refs", [])}}
                 for link in item.get("linked_candidate_ids", []) if link in candidates],
        "sources": sources, "evidence": item.get("evidence", {})})


def _evidence(item: dict, references: dict, candidates: dict) -> str:
    return _digest({"sources": {ref: references.get(ref) for ref in item.get("source_refs", [])},
        "evidence": item.get("evidence", {}),
        "linked_sources": [{ref: references.get(ref) for ref in candidates[link].get("source_refs", [])}
                           for link in item.get("linked_candidate_ids", []) if link in candidates]})


def reconcile_discovery_draft(draft: dict, baseline: dict | None, mode: str = "update") -> dict:
    if mode not in {"update", "extend", "restart"}:
        raise ValueError("Modo de generacion invalido")
    result = deepcopy(draft)
    previous = deepcopy(baseline) if baseline and mode != "restart" else None
    previous_ids = _identities(previous) if previous else {}
    if previous:
        for group, id_field, type_field in (("candidates", "candidate_id", "candidate_type"),
                                            ("model_elements", "element_id", "element_type")):
            for item in result.get(group, []):
                hint = item.get("existing_id")
                matches = [old for old in previous.get(group, []) if not old.get("change_of") and
                    old[type_field] == item[type_field] and
                    (old[id_field] == hint if hint else _normalize(old["name"]) == _normalize(item["name"]))]
                if hint and len(matches) != 1:
                    raise ValueError("Correspondencia previa invalida")
                if len(matches) == 1:
                    old = matches[0]
                    new_ids = _identities(result)
                    new_links = [new_ids.get(link, link) for link in item.get("linked_candidate_ids", [])]
                    old_links = [previous_ids.get(link, link) for link in old.get("linked_candidate_ids", [])]
                    if new_links == old_links and item.get("source_id", "") == old.get("source_id", ""):
                        item["identity_key"] = previous_ids[old[id_field]]
                    elif hint:
                        raise ValueError("La correspondencia cambia la entidad propietaria o los extremos")
    fresh_ids = _identities(result)
    old_by_key = {}
    if previous:
        for group, id_field in (("candidates", "candidate_id"), ("model_elements", "element_id")):
            for item in previous.get(group, []):
                if item.get("change_of"):
                    continue
                identity = previous_ids[item[id_field]]
                if identity in old_by_key:
                    raise ValueError("La base contiene identidades ambiguas. Consolida sus duplicados antes de actualizar.")
                old_by_key[identity] = item
    remapped = {}
    for group, id_field, prefix in (("candidates", "candidate_id", "knowledge"),
                                     ("model_elements", "element_id", "model")):
        seen = set()
        for item in result.get(group, []):
            identifier = item[id_field]
            identity = fresh_ids[identifier]
            if identity in seen:
                raise ValueError("La propuesta contiene identidades duplicadas")
            seen.add(identity)
            old = old_by_key.get(identity)
            remapped[identifier] = old[id_field] if old else f"{prefix}-{identity[:24]}"
            item["identity_key"] = identity
    reference_map = result["manifest"].get("discovery", {}).get("references", {})
    old_references = previous["manifest"].get("discovery", {}).get("references", {}) if previous else {}
    fresh_candidates = {item["candidate_id"]: item for item in deepcopy(result["candidates"])}
    old_candidates = {item["candidate_id"]: item for item in previous["candidates"]} if previous else {}
    summary = {"new": 0, "regenerated": 0, "preserved": 0, "changes": 0, "not_observed": 0}
    observed = set()
    for group, id_field in (("candidates", "candidate_id"), ("model_elements", "element_id")):
        output = []
        prior_changes = {item[id_field]: item for item in previous.get(group, [])
                         if item.get("change_of")} if previous else {}
        for item in result.get(group, []):
            identifier = item[id_field]
            identity = item["identity_key"]
            observed.add(identity)
            fingerprint = _material(item, fresh_ids, reference_map, fresh_candidates)
            item["material_fingerprint"] = fingerprint
            evidence_fingerprint = _evidence(item, reference_map, fresh_candidates)
            item["evidence_fingerprint"] = evidence_fingerprint
            item[id_field] = remapped[identifier]
            item["linked_candidate_ids"] = [remapped.get(link, link) for link in item.get("linked_candidate_ids", [])]
            old = old_by_key.get(identity)
            if old and old.get("status") in {"approved", "rejected"}:
                retained = deepcopy(old)
                retained["identity_key"] = identity
                retained.setdefault("source_snapshot", {ref: deepcopy(old_references.get(ref))
                                                         for ref in old.get("source_refs", [])})
                old_fingerprint = old.get("material_fingerprint") or _material(old, previous_ids, old_references, old_candidates)
                retained["material_fingerprint"] = old_fingerprint
                old_evidence = old.get("evidence_fingerprint") or _evidence(old, old_references, old_candidates)
                retained["evidence_fingerprint"] = old_evidence
                output.append(retained)
                summary["preserved"] += 1
                rejected_change = any(value.get("identity_key") == identity and value.get("status") == "rejected"
                    and value.get("evidence_fingerprint") == evidence_fingerprint for value in prior_changes.values())
                if fingerprint != old_fingerprint and not rejected_change and (old["status"] == "approved" or evidence_fingerprint != old_evidence):
                    change_id = f"change-{_digest([identity, fingerprint])[:24]}"
                    change = prior_changes.get(change_id)
                    if not change or change.get("status") == "pending_review":
                        change = item
                        change.update({id_field: change_id, "change_of": old[id_field],
                            "change_kind": "reconsideration" if old["status"] == "rejected" else "modification",
                            "status": "pending_review", "decision": None})
                    output.append(change)
                    summary["changes"] += 1
            else:
                output.append(item)
                summary["regenerated" if old else "new"] += 1
        if previous:
            for item in previous.get(group, []):
                if item.get("change_of"):
                    if item.get("status") == "rejected" and not any(value[id_field] == item[id_field] for value in output):
                        output.append(deepcopy(item))
                    continue
                if item.get("status") not in {"approved", "rejected"}:
                    continue
                identity = previous_ids[item[id_field]]
                if identity not in observed:
                    retained = deepcopy(item)
                    retained["identity_key"] = identity
                    retained.setdefault("source_snapshot", {ref: deepcopy(old_references.get(ref))
                                                             for ref in item.get("source_refs", [])})
                    output.append(retained)
                    summary["preserved"] += 1
                    summary["not_observed"] += 1
        result[group] = output
    candidate_ids = {item["candidate_id"] for item in result["candidates"]}
    for item in result["candidates"] + result.get("model_elements", []):
        for link in item.get("linked_candidate_ids", []):
            if link not in candidate_ids:
                dependency = old_candidates.get(link)
                if dependency is None:
                    raise ValueError("La propuesta deja un vinculo sin entidad")
                retained = deepcopy(dependency)
                retained["identity_key"] = previous_ids[link]
                result["candidates"].append(retained)
                candidate_ids.add(link)
                summary["preserved"] += 1
    if previous:
        for group in ("review_decisions", "model_element_decisions"):
            result[group] = deepcopy(previous.get(group, [])) + result.get(group, [])
    result["manifest"]["lifecycle"] = {"mode": mode,
        "base_draft_id": baseline["manifest"]["draft_id"] if baseline else None,
        "summary": summary, "applied_changes": deepcopy(previous["manifest"].get("lifecycle", {}).get("applied_changes", [])) if previous else []}
    return result


def apply_approved_change(draft: dict, group: str, item: dict) -> None:
    if item.get("status") != "approved" or not item.get("change_of"):
        return
    id_field = "candidate_id" if group == "candidates" else "element_id"
    target = next((value for value in draft[group] if value[id_field] == item["change_of"]), None)
    if target is None:
        raise ValueError("El elemento original de la propuesta de cambio no existe")
    draft["manifest"].setdefault("lifecycle", {}).setdefault("applied_changes", []).append({
        "before": deepcopy(target), "proposal": deepcopy(item), "decision": deepcopy(item.get("decision"))})
    replacement = deepcopy(item)
    replacement[id_field] = target[id_field]
    replacement.pop("change_of", None)
    replacement.pop("change_kind", None)
    draft[group] = [replacement if value is target else value for value in draft[group] if value is not item]