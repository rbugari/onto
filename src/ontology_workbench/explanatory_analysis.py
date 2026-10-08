from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from ontology_workbench.context_scanner import LlmSettings, _chunk_batches, call_llm_json, LLM_BATCH_CHAR_LIMIT
from ontology_workbench.explanatory_coverage import build_explanatory_coverage


PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "atlas_explanatory_coverage.md"
PROMPT_VERSION = "atlas-semantic-contrast-v2-inferences"
ELEMENT_BATCH_SIZE = 12
DEFAULT_MAX_CALLS = 40


def _validate_response(response: dict, elements: list[dict], chunks: list[dict]) -> list[dict]:
    if not isinstance(response, dict) or set(response) != {"evaluations"} or not isinstance(response["evaluations"], list):
        raise ValueError("invalid_response_schema")
    expected = {element["element_id"]: element for element in elements}
    evidence = {chunk["chunk_id"]: chunk for chunk in chunks}
    seen = set()
    results = []
    for result in response["evaluations"]:
        required = {"element_id", "reason", "supports", "contradictions"}
        if not isinstance(result, dict) or not required <= set(result) or set(result) - required - {"inferences"}:
            raise ValueError("invalid_evaluation_schema")
        element_id = result["element_id"]
        if not isinstance(element_id, str) or element_id not in expected or element_id in seen:
            raise ValueError("invalid_element_id")
        if not isinstance(result["reason"], str) or not result["reason"].strip():
            raise ValueError("missing_reason")
        seen.add(element_id)
        for field in ("supports", "contradictions"):
            if not isinstance(result[field], list):
                raise ValueError("invalid_claims")
            for claim in result[field]:
                keys = {"aspect", "chunk_id", "quote"} if field == "supports" else {"chunk_id", "quote", "reason", "material"}
                if not isinstance(claim, dict) or set(claim) != keys:
                    raise ValueError("invalid_claim_schema")
                chunk_id, quote = claim["chunk_id"], claim["quote"]
                if not isinstance(chunk_id, str) or chunk_id not in evidence:
                    raise ValueError("invalid_chunk_id")
                if not isinstance(quote, str) or not quote.strip() or quote not in evidence[chunk_id]["text"]:
                    raise ValueError("invalid_quote")
                if field == "supports" and claim["aspect"] not in expected[element_id]["required_aspects"]:
                    raise ValueError("invalid_aspect")
                if field == "contradictions" and (not isinstance(claim["material"], bool)
                    or not isinstance(claim["reason"], str) or not claim["reason"].strip()):
                    raise ValueError("invalid_contradiction")
        inferences = result.get("inferences", [])
        if not isinstance(inferences, list):
            raise ValueError("invalid_inferences")
        for inference in inferences:
            if not isinstance(inference, dict) or set(inference) != {
                "aspect", "explanation", "basis", "assumptions", "validation_needed", "related_evidence"
            }:
                raise ValueError("invalid_inference_schema")
            if inference["aspect"] not in expected[element_id]["required_aspects"]:
                raise ValueError("invalid_inference_aspect")
            for field in ("explanation", "basis"):
                if not isinstance(inference[field], str) or not inference[field].strip():
                    raise ValueError("invalid_inference_text")
            for field in ("assumptions", "validation_needed"):
                if not isinstance(inference[field], list) or not inference[field] or any(
                    not isinstance(value, str) or not value.strip() for value in inference[field]
                ):
                    raise ValueError("invalid_inference_review")
            if not isinstance(inference["related_evidence"], list):
                raise ValueError("invalid_inference_evidence")
            for citation in inference["related_evidence"]:
                if not isinstance(citation, dict) or set(citation) != {"chunk_id", "quote"}:
                    raise ValueError("invalid_inference_citation")
                chunk_id, quote = citation["chunk_id"], citation["quote"]
                if not isinstance(chunk_id, str) or chunk_id not in evidence or not isinstance(quote, str) or not quote.strip() or quote not in evidence[chunk_id]["text"]:
                    raise ValueError("invalid_inference_quote")
        results.append(deepcopy(result))
    if seen != set(expected):
        raise ValueError("missing_elements")
    return results


def analyze_explanatory_scope(scope: dict, chunks: list[dict], settings: LlmSettings,
                              max_calls: int = DEFAULT_MAX_CALLS, cached: dict | None = None) -> dict:
    if isinstance(max_calls, bool) or not isinstance(max_calls, int) or not 1 <= max_calls <= 200:
        raise ValueError("El limite de llamadas debe estar entre 1 y 200.")
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    configuration = {key: getattr(settings, key) for key in (
        "provider", "model", "base_url", "endpoint", "deployment", "api_version", "reasoning_effort", "data_policy")}
    configuration["model"] = settings.deployment or settings.model if settings.provider == "azure_openai" else (
        settings.model or "llama3.1:8b" if settings.provider == "ollama" else settings.model)
    targets = [{key: element[key] for key in ("element_id", "kind", "name", "source_names", "technical_reference", "required_aspects")}
               for element in scope["elements"] if element["included"]]
    scope_elements = {element["element_id"]: element for element in scope["elements"]}
    for target in targets:
        if target["kind"] == "relationship":
            target["endpoints"] = [{"element_id": endpoint, "name": scope_elements[endpoint]["name"],
                                    "technical_reference": scope_elements[endpoint]["technical_reference"]}
                                   for endpoint in target["technical_reference"][:2] if endpoint in scope_elements]
    unique_chunks = []
    content_hashes = set()
    ambiguous = build_explanatory_coverage(scope, chunks)["ambiguous_chunk_ids"]
    for chunk in sorted(chunks, key=lambda item: item["chunk_id"]):
        content_hash = hashlib.sha256(chunk["text"].encode()).hexdigest()
        if chunk["chunk_id"] not in ambiguous and content_hash not in content_hashes:
            content_hashes.add(content_hash)
            unique_chunks.append(chunk)
    fingerprint = hashlib.sha256(json.dumps({
        "scope": scope["scope_version"], "targets": targets, "chunks": unique_chunks,
        "evidence_hashes": sorted({(chunk["chunk_id"], hashlib.sha256(chunk["text"].encode()).hexdigest()) for chunk in chunks}),
        "configuration": configuration, "prompt": prompt, "max_calls": max_calls,
    }, sort_keys=True).encode()).hexdigest()
    analysis = {"prompt_version": PROMPT_VERSION, "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest(),
                "configuration": configuration, "fingerprint": fingerprint, "max_calls": max_calls,
                "calls": [], "calls_made": 0, "cache_reused": False, "status": "not_evaluated",
                "effective_mode": "none", "human_review_required": True, "human_review_sample": []}
    if not settings.enabled or settings.provider not in {"openai", "azure_openai", "ollama"}:
        analysis["status"] = "blocked_by_policy" if settings.data_policy == "local_only" and settings.provider != "ollama" else "provider_unavailable"
    elif not targets:
        analysis["status"] = "no_scope"
    elif not unique_chunks:
        analysis["status"] = "no_evidence"
    else:
        if (cached and cached.get("analysis", {}).get("fingerprint") == fingerprint
            and cached.get("analysis", {}).get("status") == "complete"):
            result = deepcopy(cached)
            result["analysis"].update(cache_reused=True, calls_made=0)
            return result
        analysis["effective_mode"] = "llm_semantic_proposals"
        decisions = []
        chunk_batches = _chunk_batches(unique_chunks)
        analysis["planned_calls"] = ((len(targets) + ELEMENT_BATCH_SIZE - 1) // ELEMENT_BATCH_SIZE) * (
            len(chunk_batches) + (1 if len(chunk_batches) > 1 else 0))

        def request(elements, evidence, phase, findings=None):
            record = {"phase": phase, "element_ids": [element["element_id"] for element in elements],
                      "chunk_ids": [chunk["chunk_id"] for chunk in evidence], "status": "failed"}
            analysis["calls"].append(record)
            if analysis["calls_made"] >= max_calls:
                record["error"] = "call_budget_exhausted"
                return None
            payload = {"phase": phase, "elements": elements,
                       "evidence": [{"chunk_id": chunk["chunk_id"], "filename": chunk.get("filename"), "text": chunk["text"]}
                                    for chunk in evidence] if phase == "contrast" else [],
                       "findings": findings or []}
            if len(json.dumps(payload)) > LLM_BATCH_CHAR_LIMIT * 2:
                record["error"] = "context_limit"
                return None
            analysis["calls_made"] += 1
            try:
                response = call_llm_json([{"role": "system", "content": prompt},
                                          {"role": "user", "content": json.dumps(payload, ensure_ascii=True)}], settings)
            except Exception as exc:
                record["error"] = f"provider_error:{type(exc).__name__}"
                return None
            try:
                validated = _validate_response(response, elements, evidence)
            except (ValueError, TypeError) as exc:
                record["error"] = str(exc) if isinstance(exc, ValueError) else "invalid_response_types"
                return None
            record["status"] = "validated"
            return validated

        for offset in range(0, len(targets), ELEMENT_BATCH_SIZE):
            elements = targets[offset:offset + ELEMENT_BATCH_SIZE]
            findings = []
            complete = True
            for batch in chunk_batches:
                proposals = request(elements, batch, "contrast")
                if proposals is None:
                    complete = False
                    break
                findings.extend(proposals)
            if complete and len(chunk_batches) > 1:
                consolidated = request(elements, unique_chunks, "consolidate", findings)
                if consolidated is None:
                    complete = False
                else:
                    for proposal in consolidated:
                        inherited = [claim for result in findings if result["element_id"] == proposal["element_id"]
                                     for claim in result["contradictions"]]
                        proposal["contradictions"].extend(inherited)
                    findings = consolidated
            for element in elements:
                result = next((proposal for proposal in findings if proposal["element_id"] == element["element_id"]), {})
                decisions.append({**result, "element_id": element["element_id"], "method": "llm_semantic_proposal",
                                  "evaluation_status": "evaluated" if complete else "failed",
                                  "reason": result.get("reason", "Contraste incompleto; sin fallback heuristico."),
                                  "supports": result.get("supports", []), "contradictions": result.get("contradictions", [])})
        coverage = build_explanatory_coverage(scope, chunks, decisions)
        coverage["inferred_explanations"] = [
            {**deepcopy(inference), "element_id": decision["element_id"],
             "origin": "model_inference", "model_contribution": "substantial",
             "review_status": "pending_review", "counts_as_documentary_support": False}
            for decision in decisions if decision["evaluation_status"] == "evaluated"
            for inference in decision.get("inferences", [])
        ]
        failed = any(row["evaluation_status"] == "failed" for row in coverage["elements"])
        analysis["status"] = "partial_failure" if failed else "complete"
        analysis["human_review_sample"] = [element_id for state in ("explained", "partial", "unexplained", "contradictory")
                            for element_id in [row["element_id"] for row in coverage["elements"]
                                       if row["state"] == state][:3]]
        coverage["analysis"] = analysis
        return coverage
    coverage = build_explanatory_coverage(scope, chunks)
    coverage["analysis"] = analysis
    return coverage