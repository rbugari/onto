from __future__ import annotations

import json

from ontology_workbench.models import OntologyProject, ValidationIssue


def export_project_json(project: OntologyProject, validation_issues: list[ValidationIssue]) -> str:
    payload = {
        "project": project.to_dict(),
        "validation": [issue.to_dict() for issue in validation_issues],
        "export_format": "ontology-workbench-v1",
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def export_project_markdown(project: OntologyProject, validation_issues: list[ValidationIssue]) -> str:
    lines = [
        f"# {project.name}",
        "",
        project.description or "Sin descripcion.",
        "",
        "## Metadata",
        "",
    ]
    if project.metadata:
        for key, value in sorted(project.metadata.items()):
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- Sin metadata")

    lines.extend(["", "## Conceptos", ""])
    if project.concepts:
        for concept in project.concepts:
            tags = ", ".join(concept.tags) if concept.tags else "sin tags"
            lines.extend(
                [
                    f"### {concept.name}",
                    f"- id: {concept.id}",
                    f"- estado: {concept.status}",
                    f"- tags: {tags}",
                    f"- definicion: {concept.definition or 'Sin definicion'}",
                    "",
                ]
            )
    else:
        lines.append("No hay conceptos cargados.")

    lines.extend(["", "## Relaciones", ""])
    if project.relations:
        for relation in project.relations:
            lines.append(
                f"- {relation.source_id} --{relation.relation_type}--> {relation.target_id}: {relation.description or 'Sin descripcion'}"
            )
    else:
        lines.append("No hay relaciones cargadas.")

    lines.extend(["", "## Validacion", ""])
    if validation_issues:
        for issue in validation_issues:
            lines.append(f"- [{issue.level}] {issue.code}: {issue.message}")
    else:
        lines.append("- Sin observaciones")
    lines.append("")
    return "\n".join(lines)
