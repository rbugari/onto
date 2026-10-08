from __future__ import annotations

from collections import Counter

from ontology_workbench.cross_source import build_cross_source_map
from ontology_workbench.explanatory_coverage import build_explanatory_coverage
from ontology_workbench.explanatory_scope import build_explanatory_scope
from ontology_workbench.models import DocumentRecord, OntologyProject, utc_now_iso


ATLAS_PRODUCT_NAME = "Atlas"
ATLAS_FORMAT_VERSION = "atlas-assessment-v0.2"
ATLAS_SCORING_PROFILE = "atlas-baseline-v1"

PLATFORM_LABELS = {
    "mariadb": "MariaDB / MySQL",
    "fabric": "Microsoft Fabric",
    "databricks": "Databricks",
    "powerbi": "Power BI (modelo semantico)",
    "sqlserver": "SQL Server",
    "postgres": "PostgreSQL",
    "snowflake": "Snowflake",
    "oracle": "Oracle",
    "files": "Planillas / archivos",
    "other": "Otro",
}


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
    explanatory_scope = build_explanatory_scope(project)
    source_inventory = _source_inventory(project, documents, source_hashes)
    cross_source_map = build_cross_source_map(
        source_inventory["technical_sources"], semantic_inventory["objects"]
    )
    scope_definition = _scope_definition(project, client_id, domain_id, data_product_id)
    gap_backlog = _gap_backlog(
        project, semantic_inventory, source_inventory, business_context, cross_source_map
    )
    readiness_score = _readiness_score(
        semantic_inventory, source_inventory, business_context, cross_source_map, scope_definition,
        high_gaps=sum(gap["severity"] == "high" for gap in gap_backlog),
    )
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
            "explanatory_scope.json",
            "explanatory_coverage.json",
            "scope_definition.json",
            "semantic_inventory.json",
            "business_context_inventory.json",
            "source_inventory.json",
            "cross_source_map.json",
            "readiness_score.json",
            "gap_backlog.json",
            "evidence_index.json",
            "assessment_review.json",
            "execution_summary.md",
        ],
        "scoring_profile": ATLAS_SCORING_PROFILE,
        "summary": {
            "overall_score": readiness_score["overall_score"],
            "interpretation": readiness_score["interpretation"],
            "technical_sources": source_inventory["summary"]["technical_sources"],
            "gaps": len(gap_backlog),
            "high_gaps": sum(gap["severity"] == "high" for gap in gap_backlog),
        },
    }
    return {
        "manifest": manifest,
        "explanatory_scope": explanatory_scope,
        "explanatory_coverage": build_explanatory_coverage(explanatory_scope, context_chunks),
        "scope_definition": scope_definition,
        "semantic_inventory": semantic_inventory,
        "business_context_inventory": business_context or _empty_business_context(),
        "source_inventory": source_inventory,
        "cross_source_map": cross_source_map,
        "evidence_index": _evidence_index(context_chunks),
        "readiness_score": readiness_score,
        "gap_backlog": gap_backlog,
        "assessment_review": _assessment_review(gap_backlog),
        "execution_summary": _execution_summary(
            manifest, scope_definition, semantic_inventory, source_inventory,
            cross_source_map, readiness_score, gap_backlog,
        ),
    }


def _scope_definition(
    project: OntologyProject, client_id: str, domain_id: str, data_product_id: str
) -> dict[str, object]:
    return {
        "client_id": client_id,
        "domain_id": domain_id,
        "data_product_id": data_product_id,
        "domain_owner": project.metadata.get("owner", ""),
        "use_cases": [use_case.to_dict() for use_case in project.use_cases],
        "sources_in_scope": [
            {"source_id": source.source_id, "name": source.name, "platform": source.platform}
            for source in project.sources
        ],
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
            "source_id": concept.metadata.get("source.id", ""),
            "status": concept.status,
            "tags": concept.tags,
            "source_ref": concept.metadata.get("bim.table") or concept.name,
            "metadata": dict(concept.metadata),
        }
        for concept in project.concepts
    ]
    by_source: dict[str, Counter] = {}
    for item in objects:
        by_source.setdefault(str(item["source_id"]) or "sin-fuente", Counter())[str(item["object_type"])] += 1
    return {
        "source_format": project.metadata.get("source.format", "manual"),
        "project_metadata": dict(project.metadata),
        "summary": {
            "concepts": len(project.concepts),
            "relations": len(project.relations),
            "tables": object_types["table"],
            "columns": object_types["column"],
            "measures": object_types["measure"],
            "by_source": {source_id: dict(counts) for source_id, counts in sorted(by_source.items())},
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
    technical_sources = _technical_sources(project)
    declared_sources = [
        _source_row(source) for source in project.sources if source.status != "inventoried"
    ]
    return {
        "summary": {
            "technical_sources": len(technical_sources),
            "declared_sources": len(declared_sources),
            "platforms": sorted({str(source["platform"]) for source in technical_sources}),
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
        "technical_sources": technical_sources,
        "declared_sources": declared_sources,
    }


def _source_row(source) -> dict[str, object]:
    return {
        "source_id": source.source_id,
        "name": source.name,
        "platform": source.platform,
        "platform_label": PLATFORM_LABELS.get(source.platform, source.platform),
        "owner": source.owner,
        "access_mode": source.access_mode,
        "status": source.status,
        "source_format": source.source_format,
        "filename": source.filename,
        "stored_path": source.stored_path,
        "content_sha256": source.content_sha256,
        "inventoried_at": source.inventoried_at,
        "object_counts": dict(source.object_counts),
        "integrity_status": "recorded" if source.stored_path and source.content_sha256 else "incomplete_record",
    }


def _technical_sources(project: OntologyProject) -> list[dict[str, object]]:
    sources = [_source_row(source) for source in project.sources if source.status == "inventoried"]
    legacy = _legacy_technical_source(project)
    if legacy and not any(
        source["content_sha256"] == legacy["content_sha256"] or source["stored_path"] == legacy["stored_path"]
        for source in sources
    ):
        sources.append(legacy)
    return sources


def _legacy_technical_source(project: OntologyProject) -> dict[str, object] | None:
    metadata = project.metadata
    source_path = metadata.get("source.technical.path", "")
    source_hash = metadata.get("source.technical.sha256", "")
    source_filename = metadata.get("source.technical.filename", "")
    if not (source_path or source_hash or source_filename):
        return None
    return {
        "source_id": "technical-model",
        "name": source_filename or "Modelo tecnico",
        "platform": "other",
        "platform_label": PLATFORM_LABELS["other"],
        "owner": "",
        "access_mode": "external_file",
        "status": "inventoried",
        "source_format": metadata.get("source.format", "unknown"),
        "filename": source_filename,
        "stored_path": source_path,
        "content_sha256": source_hash,
        "inventoried_at": "",
        "object_counts": {},
        "integrity_status": "recorded" if source_path and source_hash else "incomplete_record",
    }


def _readiness_score(
    semantic_inventory: dict[str, object],
    source_inventory: dict[str, object],
    business_context: dict[str, object] | None,
    cross_source_map: dict[str, object],
    scope_definition: dict[str, object],
    high_gaps: int = 0,
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
    if scope_definition.get("use_cases"):
        governance_score += 1

    dimensions = [
        _dimension("semantic_metadata", semantic_score, "Cobertura de objetos tecnicos extraidos."),
        _dimension("business_context", business_score, "Documentacion y contexto funcional disponible."),
        _dimension("semantic_business_linkage", linkage_score, "Cruce basal entre fuentes tecnicas y funcionales."),
        _dimension("governance_traceability", governance_score, "Evidencia, casos de uso y estructura disponibles para iniciar revision."),
    ]
    if source_summary["technical_sources"] + source_summary["declared_sources"] >= 2:
        dimensions.append(
            _dimension(
                "cross_source_alignment",
                _cross_source_score(source_inventory, cross_source_map),
                "Cobertura de sistemas en alcance, entidades compartidas, claves comunes y responsables.",
            )
        )
    overall = round(sum(item["score"] for item in dimensions) / len(dimensions), 2)
    interpretation = _readiness_label(overall)
    if high_gaps and interpretation == "strong_foundation":
        interpretation = "partial_foundation"
    return {
        "profile": ATLAS_SCORING_PROFILE,
        "scale": "0-5",
        "overall_score": overall,
        "interpretation": interpretation,
        "high_gaps": high_gaps,
        "dimensions": dimensions,
        "warning": (
            "Score basal determinista: orienta el assessment inicial y no sustituye "
            "la validacion humana ni el scoring de readiness final."
        ),
    }


def _dimension(name: str, score: int, evidence: str) -> dict[str, object]:
    return {"dimension": name, "score": score, "max_score": 5, "evidence": evidence}


def _cross_source_score(source_inventory: dict[str, object], cross_source_map: dict[str, object]) -> int:
    summary = dict(cross_source_map["summary"])
    score = 1 if source_inventory["summary"]["technical_sources"] >= 2 else 0
    if not source_inventory["summary"]["declared_sources"]:
        score += 1
    if summary["shared_entities"]:
        score += 1
    if summary["shared_with_common_key"] and summary["shared_with_common_key"] == summary["shared_entities"]:
        score += 1
    all_sources = [*source_inventory["technical_sources"], *source_inventory["declared_sources"]]
    if all(source.get("owner") for source in all_sources):
        score += 1
    return min(score, 5)


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
    cross_source_map: dict[str, object],
) -> list[dict[str, object]]:
    summary = dict(semantic_inventory["summary"])
    source_summary = dict(source_inventory["summary"])
    gaps: list[dict[str, object]] = []
    use_cases_by_source: dict[str, list[str]] = {}
    for use_case in project.use_cases:
        for source_id in use_case.source_ids:
            use_cases_by_source.setdefault(source_id, []).append(use_case.use_case_id)

    def add_gap(
        code: str, severity: str, message: str, recommendation: str,
        category: str = "gobierno", source_id: str = "", use_case_ids: list[str] | None = None,
    ) -> None:
        gaps.append(
            {
                "gap_id": code,
                "severity": severity,
                "category": category,
                "source_id": source_id,
                "use_case_ids": use_case_ids if use_case_ids is not None else use_cases_by_source.get(source_id, []),
                "message": message,
                "recommendation": recommendation,
            }
        )

    if not project.use_cases:
        add_gap(
            "missing-use-cases", "medium",
            "El assessment no declara casos de uso; no se puede priorizar que brechas bloquean valor.",
            "Registrar uno o dos casos de uso con su pregunta de negocio, responsable y sistemas involucrados.",
            category="alcance",
        )
    if not summary["tables"]:
        add_gap("missing-semantic-model", "high", "No se detectaron tablas o un modelo semantico estructurado.", "Incorporar metadata de al menos un sistema: model.bim, PBIP/TMDL, DDL, export de information_schema o Fabric.", category="fuentes")
    elif not source_summary["technical_sources"]:
        add_gap(
            "missing-technical-source-evidence",
            "medium",
            "El modelo semantico existe en ONTO, pero no hay archivo tecnico original con hash asociado al assessment.",
            "Reimportar el archivo tecnico original mediante Atlas para conservar la evidencia local y su hash.",
            category="fuentes",
        )
    for source in project.sources:
        if source.status != "inventoried":
            add_gap(
                f"source-not-inventoried:{source.source_id}", "high",
                f"El sistema '{source.name}' esta en alcance pero no tiene metadata inventariada.",
                "Cargar su DDL, export de information_schema o modelo semantico, o conectarlo en modo solo lectura.",
                category="fuentes", source_id=source.source_id,
            )
        if not source.owner:
            add_gap(
                f"source-without-owner:{source.source_id}", "medium",
                f"El sistema '{source.name}' no tiene responsable declarado.",
                "Asignar un responsable tecnico o funcional que valide sus objetos y definiciones.",
                category="gobierno", source_id=source.source_id,
            )
    known_source_ids = {source.source_id for source in project.sources}
    for use_case in project.use_cases:
        missing = [source_id for source_id in use_case.source_ids if source_id not in known_source_ids]
        if not use_case.source_ids:
            add_gap(
                f"use-case-without-sources:{use_case.use_case_id}", "medium",
                f"El caso de uso '{use_case.name}' no indica que sistemas necesita.",
                "Vincular el caso de uso con los sistemas que contienen los datos requeridos.",
                category="alcance", use_case_ids=[use_case.use_case_id],
            )
        elif missing:
            add_gap(
                f"use-case-unknown-sources:{use_case.use_case_id}", "medium",
                f"El caso de uso '{use_case.name}' referencia sistemas no registrados: {', '.join(missing)}.",
                "Registrar esos sistemas en Fuentes o corregir el vinculo del caso de uso.",
                category="alcance", use_case_ids=[use_case.use_case_id],
            )
    by_source = dict(summary.get("by_source", {}))
    if project.sources and by_source.get("sin-fuente"):
        add_gap(
            "objects-without-source", "low",
            f"Hay {sum(by_source['sin-fuente'].values())} objetos tecnicos sin sistema de origen asignado.",
            "Reimportar esos objetos desde la fuente correspondiente para conservar la trazabilidad por sistema.",
            category="fuentes",
        )
    if source_summary["technical_sources"] >= 2:
        cross_summary = dict(cross_source_map["summary"])
        if not cross_summary["shared_entities"]:
            add_gap(
                "no-shared-entities-across-sources", "high",
                "Ninguna entidad aparece en mas de un sistema con nombre reconocible; la ontologia comun no tiene puntos de anclaje.",
                "Realizar un taller de equivalencias (por ejemplo Cliente = Cuenta CRM) y documentarlas en el glosario.",
                category="entre_sistemas", use_case_ids=[],
            )
        for row in cross_source_map["shared_entities"]:
            if not row.get("common_key"):
                add_gap(
                    f"shared-entity-without-common-key:{row['entity']}", "medium",
                    f"La entidad '{row['entity']}' existe en {', '.join(row['sources'])} sin una clave comun identificable.",
                    "Documentar como se cruza la entidad entre sistemas (clave, tabla de equivalencias o regla de matching).",
                    category="entre_sistemas",
                    use_case_ids=sorted({uc for source_id in row["source_ids"] for uc in use_cases_by_source.get(source_id, [])}),
                )
    if not source_summary["documents"]:
        add_gap("missing-business-sources", "high", "No hay documentacion funcional o de negocio cargada.", "Cargar glosarios, definiciones de KPI, procesos o documentacion funcional vigente.", category="negocio")
    if source_summary["duplicate_document_ids"]:
        add_gap(
            "duplicate-document-identifiers",
            "high",
            "Existen documentos heredados con identificadores duplicados; la evidencia extraida puede no ser trazable.",
            "Regenerar las extracciones afectadas con identificadores unicos antes de usar el contexto para una release.",
            category="negocio",
        )
    if not _context_is_available(business_context):
        add_gap("business-context-not-scanned", "medium", "No existe un inventario de contexto de negocio para esta ejecucion.", "Ejecutar el scanner documental y revisar sus resultados antes de generar candidatos ontologicos.", category="negocio")
    else:
        pending_definitions = sum(item.get("status") != "approved" for item in business_context.get("definitions", []) if isinstance(item, dict))
        if pending_definitions:
            add_gap("definitions-pending-review", "medium", f"Hay {pending_definitions} definiciones extraidas sin aprobacion humana.", "Planificar una revision funcional de terminos y definiciones candidatas.", category="negocio")
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
    scope_definition: dict[str, object],
    semantic_inventory: dict[str, object],
    source_inventory: dict[str, object],
    cross_source_map: dict[str, object],
    readiness_score: dict[str, object],
    gap_backlog: list[dict[str, object]],
) -> str:
    scope = dict(manifest["scope"])
    summary = dict(semantic_inventory["summary"])
    source_summary = dict(source_inventory["summary"])
    dimensions = list(readiness_score["dimensions"])
    lines = [
        "# Diagnostico de preparacion para agentes", "",
        f"- Ejecucion: `{manifest['run_id']}`",
        f"- Cliente: `{scope['client_id']}`", f"- Dominio: `{scope['domain_id']}`",
        f"- Data product: `{scope['data_product_id']}`", "",
        "## Lectura ejecutiva", "",
        f"- Fundacion observada: {readiness_score['interpretation']} ({readiness_score['overall_score']}/5).",
        f"- Sistemas inventariados: {source_summary['technical_sources']}"
        f" ({', '.join(source_summary['platforms']) or 'ninguno'}).",
        f"- Brechas detectadas: {len(gap_backlog)}"
        f" ({sum(gap['severity'] == 'high' for gap in gap_backlog)} altas);"
        " requieren validacion de alcance y prioridad con el cliente.",
        "- Esta puntuacion es basal: no certifica que los datos esten listos para agentes.",
        "", "## Casos de uso evaluados", "",
    ]
    use_cases = list(scope_definition.get("use_cases", []))
    if use_cases:
        for use_case in use_cases:
            lines.append(
                f"- **{use_case['name']}** (prioridad {use_case['priority']}; responsable "
                f"{use_case['owner'] or 'sin asignar'}): {use_case['business_question'] or 'sin pregunta declarada'}"
                f" Sistemas: {', '.join(use_case['source_ids']) or 'sin vincular'}."
            )
    else:
        lines.append("- No se declararon casos de uso.")
    lines.extend([
        "", "## Sistemas en alcance", "",
        "| Sistema | Plataforma | Responsable | Estado | Tablas | Columnas | Formato |",
        "| --- | --- | --- | --- | ---: | ---: | --- |",
    ])
    for source in [*source_inventory["technical_sources"], *source_inventory.get("declared_sources", [])]:
        counts = dict(source.get("object_counts", {}))
        lines.append(
            f"| {source['name']} | {source['platform_label']} | {source['owner'] or 'sin asignar'} | "
            f"{source['status']} | {counts.get('tables', '-')} | {counts.get('columns', '-')} | "
            f"{source['source_format'] or '-'} |"
        )
    cross_summary = dict(cross_source_map["summary"])
    lines.extend([
        "", "## Mapa entre sistemas", "",
        f"- Entidades detectadas: {cross_summary['entities']}; presentes en mas de un sistema: "
        f"{cross_summary['shared_entities']} (con clave comun: {cross_summary['shared_with_common_key']}).",
    ])
    for row in cross_source_map["shared_entities"]:
        lines.append(
            f"- `{row['entity']}` en {', '.join(row['sources'])}; clave comun: "
            f"{row.get('common_key') or 'no identificada'}."
        )
    lines.append(f"- Nota: {cross_source_map['warning']}")
    lines.extend([
        "", "## Evidencia documental", "",
        f"- Documentos: {source_summary['documents']} ({source_summary['extracted_documents']} extraidos).",
    ])
    for source in source_inventory["sources"]:
        lines.append(
            f"- {source['filename']} (`{source['source_id']}`): {source['extraction_status']}; "
            f"hash SHA-256 `{source['content_sha256'] or 'no disponible'}`."
        )
    for source in source_inventory["technical_sources"]:
        lines.append(
            f"- Metadata tecnica {source['name']} ({source['filename'] or 'sin archivo'}): {source['integrity_status']}; "
            f"hash SHA-256 `{source['content_sha256'] or 'no disponible'}`."
        )
    lines.extend(["", "## Inventario tecnico", "",
        f"- Conceptos: {summary['concepts']}", f"- Relaciones: {summary['relations']}",
        f"- Tablas: {summary['tables']}", f"- Columnas: {summary['columns']}",
        f"- Medidas: {summary['measures']}", "", "## Evaluacion basal", "",
        "| Dimension | Puntaje / 5 | Evidencia usada |", "| --- | ---: | --- |",
    ])
    for dimension in dimensions:
        lines.append(
            f"| {dimension['dimension']} | {dimension['score']} | {dimension['evidence']} |"
        )
    lines.extend(["", "## Brechas y acciones sugeridas", ""])
    if gap_backlog:
        for gap in gap_backlog:
            context = f"Categoria: {gap.get('category', 'gobierno')}"
            if gap.get("source_id"):
                context += f" · Sistema: {gap['source_id']}"
            if gap.get("use_case_ids"):
                context += f" · Casos de uso: {', '.join(gap['use_case_ids'])}"
            lines.extend([
                f"### {gap['gap_id']} ({gap['severity']})", "",
                gap["message"], "", context, "",
                f"Accion sugerida: {gap['recommendation']}", "",
            ])
    else:
        lines.extend(["No se detectaron brechas con las reglas basales; hace falta revision funcional.", ""])
    lines.extend([
        "## Siguientes pasos", "",
        "1. Confirmar alcance, fuentes y brechas con responsables de negocio y datos.",
        "2. Completar y revisar glosario, KPIs, reglas y vinculos entre conceptos y fuentes.",
        "3. Elegir con el cliente el destino de implementacion y validar sus requisitos especificos.",
        "", "## Limites del diagnostico", "",
        "Este informe describe evidencia disponible y reglas basales; no es una certificacion de calidad, "
        "permisos, seguridad ni preparacion productiva para agentes.",
        "Las definiciones extraidas son candidatas hasta que un responsable las revise. "
        "No se publica conocimiento en Fabric, Databricks ni otros destinos.",
        "La revision humana del assessment se registra por separado en assessment_review.json.", "",
    ])
    return "\n".join(lines)
