from __future__ import annotations

from collections import Counter

from ontology_workbench.models import DocumentRecord, OntologyProject, utc_now_iso


ATLAS_PRODUCT_NAME = "Atlas"
ATLAS_FORMAT_VERSION = "atlas-assessment-v0.1"


def build_assessment_package(
    project: OntologyProject,
    documents: list[DocumentRecord],
    business_context: dict[str, object] | None,
    context_chunks: list[dict[str, object]],
    source_hashes: dict[str, str],
    client_id: str,
    domain_id: str,
    data_product_id: str,
    run_id: str,
) -> dict[str, object]:
    """Build the first deterministic Atlas assessment package from local MVP evidence."""
    semantic_inventory = _semantic_inventory(project)
    source_inventory = _source_inventory(project, documents, source_hashes)
    readiness_score = _readiness_score(semantic_inventory, source_inventory, business_context)
    gap_backlog = _gap_backlog(project, semantic_inventory, source_inventory, business_context)
    manifest = {
        "format": ATLAS_FORMAT_VERSION,
        "product": ATLAS_PRODUCT_NAME,
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "scope": {
            "project_id": project.id,
            "client_id": client_id,
            "domain_id": domain_id,
            "data_product_id": data_product_id,
        },
        "artifacts": [
            "semantic_inventory.json",
            "business_context_inventory.json",
            "source_inventory.json",
            "readiness_score.json",
            "gap_backlog.json",
            "evidence_index.json",
            "assessment_review.json",
            "execution_summary.md",
        ],
        "scoring_profile": "atlas-baseline-v0",
    }
    return {
        "manifest": manifest,
        "semantic_inventory": semantic_inventory,
        "business_context_inventory": business_context or _empty_business_context(),
        "source_inventory": source_inventory,
        "evidence_index": _evidence_index(context_chunks),
        "readiness_score": readiness_score,
        "gap_backlog": gap_backlog,
        "assessment_review": _assessment_review(gap_backlog),
        "execution_summary": _execution_summary(manifest, semantic_inventory, readiness_score, gap_backlog),
    }


def _evidence_index(chunks: list[dict[str, object]]) -> dict[str, object]:
    return {
        "summary": {"chunks": len(chunks)},
        "chunks": [
            {
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["document_id"],
                "filename": chunk["filename"],
                "chunk_index": chunk["chunk_index"],
                "char_start": chunk["char_start"],
                "char_end": chunk["char_end"],
                "excerpt": str(chunk["text"])[:600],
            }
            for chunk in chunks
        ],
    }


def _assessment_review(gap_backlog: list[dict[str, str]]) -> dict[str, object]:
    """Create the human checkpoint for an assessment, not an ontology approval."""
    open_gaps = [gap["gap_id"] for gap in gap_backlog]
    requirements = [
        {
            "requirement_id": "confirm-assessment-baseline",
            "status": "open",
            "message": "Confirmar que fuentes, alcance y score representan el baseline a revisar.",
        }
    ]
    requirements.extend(
        {
            "requirement_id": gap["gap_id"],
            "status": "open",
            "message": gap["recommendation"],
        }
        for gap in gap_backlog
    )
    return {
        "status": "pending_review",
        "scope": "assessment_baseline_only",
        "warning": "Esta decision no aprueba ni publica una ontologia; solo registra la revision del assessment Atlas.",
        "reviewed_at": None,
        "reviewer": "",
        "reviewer_role": "",
        "note": "",
        "open_gap_ids": open_gaps,
        "review_requirements": requirements,
    }


def _semantic_inventory(project: OntologyProject) -> dict[str, object]:
    object_types = Counter(_concept_object_type(concept.tags, concept.metadata) for concept in project.concepts)
    objects = [
        {
            "object_id": concept.id,
            "name": concept.name,
            "object_type": _concept_object_type(concept.tags, concept.metadata),
            "status": concept.status,
            "tags": concept.tags,
            "source_ref": concept.metadata.get("bim.table") or concept.name,
            "metadata": dict(concept.metadata),
        }
        for concept in project.concepts
    ]
    return {
        "source_format": project.metadata.get("source.format", "manual"),
        "project_metadata": dict(project.metadata),
        "summary": {
            "concepts": len(project.concepts),
            "relations": len(project.relations),
            "tables": object_types["table"],
            "columns": object_types["column"],
            "measures": object_types["measure"],
        },
        "objects": objects,
        "relationships": [relation.to_dict() for relation in project.relations],
    }


def _concept_object_type(tags: list[str], metadata: dict[str, str]) -> str:
    object_type = metadata.get("bim.objectType", "").strip().lower()
    if object_type:
        return object_type
    tag_values = {tag.lower() for tag in tags}
    for candidate in ("table", "column", "measure"):
        if candidate in tag_values:
            return candidate
    return "concept"


def _source_inventory(
    project: OntologyProject, documents: list[DocumentRecord], source_hashes: dict[str, str]
) -> dict[str, object]:
    document_id_counts = Counter(document.document_id for document in documents)
    technical_source = _technical_source(project)
    return {
        "summary": {
            "technical_sources": 1 if technical_source else 0,
            "documents": len(documents),
            "extracted_documents": sum(document.extraction_status == "extracted" for document in documents),
            "duplicate_document_ids": sum(count - 1 for count in document_id_counts.values() if count > 1),
        },
        "sources": [
            {
                "source_id": document.document_id,
                "source_reference": _source_reference(document),
                "filename": document.filename,
                "document_type": document.doc_type,
                "content_type": document.content_type,
                "extraction_status": document.extraction_status,
                "extracted_chars": document.extracted_chars,
                "content_sha256": source_hashes.get(_source_reference(document), ""),
            }
            for document in documents
        ],
        "technical_sources": [technical_source] if technical_source else [],
    }


def _technical_source(project: OntologyProject) -> dict[str, str] | None:
    metadata = project.metadata
    source_path = metadata.get("source.technical.path", "")
    source_hash = metadata.get("source.technical.sha256", "")
    source_filename = metadata.get("source.technical.filename", "")
    if not (source_path or source_hash or source_filename):
        return None
    return {
        "source_id": "technical-model",
        "source_format": metadata.get("source.format", "unknown"),
        "filename": source_filename,
        "stored_path": source_path,
        "content_sha256": source_hash,
        "integrity_status": "recorded" if source_path and source_hash else "incomplete_record",
    }


def _readiness_score(
    semantic_inventory: dict[str, object],
    source_inventory: dict[str, object],
    business_context: dict[str, object] | None,
) -> dict[str, object]:
    summary = dict(semantic_inventory["summary"])
    source_summary = dict(source_inventory["summary"])
    context_available = _context_is_available(business_context)
    semantic_score = 0
    if summary["tables"]:
        semantic_score += 2
    if summary["columns"]:
        semantic_score += 1
    if summary["measures"]:
        semantic_score += 1
    if summary["relations"]:
        semantic_score += 1

    business_score = 0
    if source_summary["documents"]:
        business_score += 2
    if context_available and business_context:
        if business_context.get("definitions"):
            business_score += 2
        if business_context.get("business_rules") or business_context.get("kpis"):
            business_score += 1

    linkage_score = 2 if semantic_score and business_score else 0
    if context_available and business_context and business_context.get("candidate_entities"):
        linkage_score += 1
    if context_available and business_context and business_context.get("candidate_relationships"):
        linkage_score += 1
    linkage_score = min(linkage_score, 5)

    governance_score = 1 if summary["concepts"] else 0
    if summary["relations"]:
        governance_score += 1
    if source_summary["documents"]:
        governance_score += 1
    if source_summary["technical_sources"]:
        governance_score += 1

    dimensions = [
        _dimension("semantic_metadata", semantic_score, "Cobertura de objetos tecnicos extraidos."),
        _dimension("business_context", business_score, "Documentacion y contexto funcional disponible."),
        _dimension("semantic_business_linkage", linkage_score, "Cruce basal entre fuentes tecnicas y funcionales."),
        _dimension("governance_traceability", governance_score, "Evidencia y estructura disponibles para iniciar revision."),
    ]
    overall = round(sum(item["score"] for item in dimensions) / len(dimensions), 2)
    return {
        "profile": "atlas-baseline-v0",
        "scale": "0-5",
        "overall_score": overall,
        "interpretation": _readiness_label(overall),
        "dimensions": dimensions,
        "warning": (
            "Score basal determinista: orienta el assessment inicial y no sustituye "
            "la validacion humana ni el scoring de readiness final."
        ),
    }


def _dimension(name: str, score: int, evidence: str) -> dict[str, object]:
    return {"dimension": name, "score": score, "max_score": 5, "evidence": evidence}


def _readiness_label(score: float) -> str:
    if score >= 4:
        return "strong_foundation"
    if score >= 2.5:
        return "partial_foundation"
    return "early_foundation"


def _gap_backlog(
    project: OntologyProject,
    semantic_inventory: dict[str, object],
    source_inventory: dict[str, object],
    business_context: dict[str, object] | None,
) -> list[dict[str, str]]:
    summary = dict(semantic_inventory["summary"])
    source_summary = dict(source_inventory["summary"])
    gaps: list[dict[str, str]] = []

    def add_gap(code: str, severity: str, message: str, recommendation: str) -> None:
        gaps.append({"gap_id": code, "severity": severity, "message": message, "recommendation": recommendation})

    if not summary["tables"]:
        add_gap("missing-semantic-model", "high", "No se detectaron tablas o un modelo semantico estructurado.", "Incorporar model.bim, PBIP/TMDL u otro adapter de metadata autorizado.")
    elif not source_summary["technical_sources"]:
        add_gap(
            "missing-technical-source-evidence",
            "medium",
            "El modelo semantico existe en ONTO, pero no hay archivo tecnico original con hash asociado al assessment.",
            "Reimportar el model.bim original mediante Atlas para conservar la evidencia tecnica local y su hash.",
        )
    if not source_summary["documents"]:
        add_gap("missing-business-sources", "high", "No hay documentacion funcional o de negocio cargada.", "Cargar glosarios, definiciones de KPI, procesos o documentacion funcional vigente.")
    if source_summary["duplicate_document_ids"]:
        add_gap(
            "duplicate-document-identifiers",
            "high",
            "Existen documentos heredados con identificadores duplicados; la evidencia extraida puede no ser trazable.",
            "Regenerar las extracciones afectadas con identificadores unicos antes de usar el contexto para una release.",
        )
    if not _context_is_available(business_context):
        add_gap("business-context-not-scanned", "medium", "No existe un inventario de contexto de negocio para esta ejecucion.", "Ejecutar el scanner documental y revisar sus resultados antes de generar candidatos ontologicos.")
    else:
        pending_definitions = sum(item.get("status") != "approved" for item in business_context.get("definitions", []) if isinstance(item, dict))
        if pending_definitions:
            add_gap("definitions-pending-review", "medium", f"Hay {pending_definitions} definiciones extraidas sin aprobacion humana.", "Planificar una revision funcional de terminos y definiciones candidatas.")
    if not project.metadata.get("owner"):
        add_gap("missing-owner", "medium", "El proyecto no declara un owner responsable del conocimiento.", "Asignar owner de negocio y steward tecnico en la metadata del assessment.")
    return gaps


def _empty_business_context() -> dict[str, object]:
    return {"status": "not_available", "message": "No se ejecuto el scanner de contexto de negocio."}


def _context_is_available(business_context: dict[str, object] | None) -> bool:
    return bool(business_context) and business_context.get("status") != "invalidated"


def _source_reference(document: DocumentRecord) -> str:
    return f"{document.document_id}:{document.filename}"


def _execution_summary(
    manifest: dict[str, object],
    semantic_inventory: dict[str, object],
    readiness_score: dict[str, object],
    gap_backlog: list[dict[str, str]],
) -> str:
    scope = dict(manifest["scope"])
    summary = dict(semantic_inventory["summary"])
    lines = [
        "# Atlas Assessment Summary", "", f"- Run: `{manifest['run_id']}`",
        f"- Cliente: `{scope['client_id']}`", f"- Dominio: `{scope['domain_id']}`",
        f"- Data product: `{scope['data_product_id']}`", "", "## Inventario", "",
        f"- Conceptos: {summary['concepts']}", f"- Relaciones: {summary['relations']}",
        f"- Tablas: {summary['tables']}", f"- Columnas: {summary['columns']}",
        f"- Medidas: {summary['measures']}", "", "## Readiness basal", "",
        f"- Score: {readiness_score['overall_score']}/5 ({readiness_score['interpretation']})",
        f"- Gaps: {len(gap_backlog)}", "",
        "Este artefacto es un baseline reproducible de Atlas y requiere revision humana.", "",
    ]
    return "\n".join(lines)
