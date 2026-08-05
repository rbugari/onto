from __future__ import annotations

import json
import re

from ontology_workbench.context_scanner import _call_llm, load_llm_settings
from ontology_workbench.models import utc_now_iso


def build_consolidation_suggestions(candidates: list[dict[str, object]]) -> dict[str, object]:
    """Suggest duplicate groups without changing a candidate or its review status."""
    settings = load_llm_settings()
    exact_groups = _exact_duplicate_groups(candidates)
    if not settings.enabled:
        return _suggestion_package(exact_groups, "deterministic", candidates)
    try:
        llm_groups = _llm_duplicate_groups(candidates, settings)
        return _suggestion_package(_merge_groups(exact_groups, llm_groups), settings.provider, candidates)
    except Exception as exc:
        package = _suggestion_package(exact_groups, "deterministic-fallback", candidates)
        package["warning"] = str(exc)
        return package


def _llm_duplicate_groups(candidates: list[dict[str, object]], settings) -> list[dict[str, object]]:
    prompt = (
        "You are curating ontology candidates. Identify only genuine duplicate or near-duplicate "
        "candidates of the SAME candidate_type. Do not infer relationships and do not decide approval. "
        "For each group select one existing canonical_candidate_id and at least one different duplicate_candidate_id. "
        "Return JSON only: {\"groups\":[{\"canonical_candidate_id\":\"...\","
        "\"duplicate_candidate_ids\":[\"...\"],\"reason\":\"...\"}]}. "
        "If there are no genuine duplicates return {\"groups\":[]}.\n\nCandidates:\n"
        + json.dumps(
            [
                {
                    "candidate_id": candidate["candidate_id"],
                    "candidate_type": candidate["candidate_type"],
                    "name": candidate["name"],
                    "definition": str(candidate["definition"])[:700],
                }
                for candidate in candidates
            ],
            ensure_ascii=False,
        )
    )
    response = _call_llm(
        [
            {"role": "system", "content": "Return strict JSON and never invent candidate IDs."},
            {"role": "user", "content": prompt},
        ],
        settings,
    )
    raw = json.loads(response)
    return _validated_groups(raw.get("groups", []), candidates)


def _exact_duplicate_groups(candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    by_key: dict[tuple[str, str], list[dict[str, object]]] = {}
    for candidate in candidates:
        key = (str(candidate["candidate_type"]), _normalize(str(candidate["name"])))
        by_key.setdefault(key, []).append(candidate)
    groups: list[dict[str, object]] = []
    for members in by_key.values():
        if len(members) < 2:
            continue
        groups.append(
            {
                "canonical_candidate_id": members[0]["candidate_id"],
                "duplicate_candidate_ids": [member["candidate_id"] for member in members[1:]],
                "reason": "Coincidencia exacta de tipo y nombre normalizado.",
            }
        )
    return groups


def _validated_groups(raw_groups: object, candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    if not isinstance(raw_groups, list):
        return []
    by_id = {str(candidate["candidate_id"]): candidate for candidate in candidates}
    consumed_ids: set[str] = set()
    groups: list[dict[str, object]] = []
    for raw_group in raw_groups:
        if not isinstance(raw_group, dict):
            continue
        canonical_id = str(raw_group.get("canonical_candidate_id", ""))
        duplicate_ids = [str(item) for item in raw_group.get("duplicate_candidate_ids", [])]
        if canonical_id not in by_id or canonical_id in consumed_ids:
            continue
        valid_duplicates = [
            candidate_id
            for candidate_id in duplicate_ids
            if candidate_id in by_id
            and candidate_id != canonical_id
            and candidate_id not in consumed_ids
            and by_id[candidate_id]["candidate_type"] == by_id[canonical_id]["candidate_type"]
        ]
        if not valid_duplicates:
            continue
        consumed_ids.add(canonical_id)
        consumed_ids.update(valid_duplicates)
        groups.append(
            {
                "canonical_candidate_id": canonical_id,
                "duplicate_candidate_ids": valid_duplicates,
                "reason": str(raw_group.get("reason", "Similaridad semantica propuesta por LLM.")).strip(),
            }
        )
    return groups


def _merge_groups(
    exact_groups: list[dict[str, object]], llm_groups: list[dict[str, object]]
) -> list[dict[str, object]]:
    accepted = list(exact_groups)
    used_ids = {
        str(group["canonical_candidate_id"])
        for group in accepted
    }
    used_ids.update(
        str(candidate_id) for group in accepted for candidate_id in group["duplicate_candidate_ids"]
    )
    for group in llm_groups:
        group_ids = {str(group["canonical_candidate_id"]), *map(str, group["duplicate_candidate_ids"])}
        if not group_ids.intersection(used_ids):
            accepted.append(group)
            used_ids.update(group_ids)
    return accepted


def _suggestion_package(
    groups: list[dict[str, object]], mode: str, candidates: list[dict[str, object]]
) -> dict[str, object]:
    suggestions = [
        {
            "suggestion_id": f"consolidation-{index:03d}",
            "status": "pending_review",
            **group,
        }
        for index, group in enumerate(groups, start=1)
    ]
    return {
        "created_at": utc_now_iso(),
        "mode": mode,
        "candidate_count": len(candidates),
        "suggestions": suggestions,
        "warning": "Las sugerencias no modifican candidatos ni decisiones de ontologia.",
    }


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())
