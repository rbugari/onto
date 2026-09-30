from __future__ import annotations

from dataclasses import dataclass

from ontology_workbench.models import Concept, Relation


@dataclass(slots=True)
class BimImportBundle:
    concepts: list[Concept]
    relations: list[Relation]
    metadata: dict[str, str]
    summary: dict[str, int]


def build_bim_import_bundle(
    payload: dict[str, object],
    existing_concept_ids: set[str],
    existing_relation_ids: set[str],
    slugify,
    source_label: str = "model.bim",
) -> BimImportBundle:
    model_payload = payload.get("model", payload)
    if not isinstance(model_payload, dict):
        raise ValueError("model.bim invalido: falta el nodo model")

    tables = model_payload.get("tables", [])
    if not isinstance(tables, list) or not tables:
        raise ValueError("model.bim invalido: no se encontraron tablas en model.tables")

    concept_ids = set(existing_concept_ids)
    relation_ids = set(existing_relation_ids)
    concepts: list[Concept] = []
    relations: list[Relation] = []
    concept_key_map: dict[tuple[str, str, str | None], str] = {}

    def next_id(seed: str, used_ids: set[str]) -> str:
        candidate = seed or "item"
        suffix = 2
        while candidate in used_ids:
            candidate = f"{seed}-{suffix}"
            suffix += 1
        used_ids.add(candidate)
        return candidate

    def add_relation(source_id: str, target_id: str, relation_type: str, description: str = "") -> None:
        relation_seed = slugify(f"{source_id}-{relation_type}-{target_id}")
        relation_id = next_id(relation_seed, relation_ids)
        relations.append(
            Relation(
                id=relation_id,
                source_id=source_id,
                target_id=target_id,
                relation_type=relation_type,
                description=description,
            )
        )

    table_count = 0
    column_count = 0
    measure_count = 0
    relationship_count = 0

    for table_raw in tables:
        if not isinstance(table_raw, dict) or not table_raw.get("name"):
            continue

        table_name = str(table_raw["name"])
        table_concept_id = next_id(slugify(f"table-{table_name}"), concept_ids)
        concept_key_map[("table", table_name, None)] = table_concept_id
        concepts.append(
            Concept(
                id=table_concept_id,
                name=table_name,
                definition=f"Tabla importada desde {source_label}: {table_name}",
                status="draft",
                tags=["table", "bim"],
                metadata={
                    "bim.objectType": "table",
                    "bim.isHidden": str(bool(table_raw.get("isHidden", False))).lower(),
                },
            )
        )
        table_count += 1

        for column_raw in table_raw.get("columns", []):
            if not isinstance(column_raw, dict) or not column_raw.get("name"):
                continue

            column_name = str(column_raw["name"])
            column_concept_id = next_id(slugify(f"column-{table_name}-{column_name}"), concept_ids)
            concept_key_map[("column", table_name, column_name)] = column_concept_id
            concepts.append(
                Concept(
                    id=column_concept_id,
                    name=f"{table_name}[{column_name}]",
                    definition=f"Columna del modelo tabular {table_name}[{column_name}]",
                    status="draft",
                    tags=["column", "bim", str(column_raw.get("dataType", "unknown"))],
                    metadata={
                        "bim.objectType": "column",
                        "bim.table": table_name,
                        "bim.dataType": str(column_raw.get("dataType", "unknown")),
                        "bim.isHidden": str(bool(column_raw.get("isHidden", False))).lower(),
                    },
                )
            )
            add_relation(table_concept_id, column_concept_id, "contains-column")
            column_count += 1

        for measure_raw in table_raw.get("measures", []):
            if not isinstance(measure_raw, dict) or not measure_raw.get("name"):
                continue

            measure_name = str(measure_raw["name"])
            measure_concept_id = next_id(slugify(f"measure-{table_name}-{measure_name}"), concept_ids)
            concept_key_map[("measure", table_name, measure_name)] = measure_concept_id
            concepts.append(
                Concept(
                    id=measure_concept_id,
                    name=f"{table_name}[{measure_name}]",
                    definition=f"Medida del modelo tabular {table_name}[{measure_name}]",
                    status="draft",
                    tags=["measure", "bim"],
                    metadata={
                        "bim.objectType": "measure",
                        "bim.table": table_name,
                        "bim.expression": str(measure_raw.get("expression", "")),
                        "bim.formatString": str(measure_raw.get("formatString", "")),
                    },
                )
            )
            add_relation(table_concept_id, measure_concept_id, "contains-measure")
            measure_count += 1

    for relationship_raw in model_payload.get("relationships", []):
        if not isinstance(relationship_raw, dict):
            continue

        from_table = str(relationship_raw.get("fromTable", "")).strip()
        from_column = str(relationship_raw.get("fromColumn", "")).strip()
        to_table = str(relationship_raw.get("toTable", "")).strip()
        to_column = str(relationship_raw.get("toColumn", "")).strip()
        if not from_table or not to_table:
            continue

        source_id = concept_key_map.get(("column", from_table, from_column)) or concept_key_map.get(("table", from_table, None))
        target_id = concept_key_map.get(("column", to_table, to_column)) or concept_key_map.get(("table", to_table, None))
        if not source_id or not target_id:
            continue

        description_parts = []
        if relationship_raw.get("crossFilteringBehavior"):
            description_parts.append(f"crossFilteringBehavior={relationship_raw['crossFilteringBehavior']}")
        if relationship_raw.get("joinOnDateBehavior"):
            description_parts.append(f"joinOnDateBehavior={relationship_raw['joinOnDateBehavior']}")
        if relationship_raw.get("isActive") is not None:
            description_parts.append(f"isActive={relationship_raw['isActive']}")

        add_relation(source_id, target_id, "bim-relationship", "; ".join(description_parts))
        relationship_count += 1

    metadata = {
        "source.format": "model.bim",
        "bim.compatibilityLevel": str(model_payload.get("compatibilityLevel", "")),
        "bim.defaultPowerBIDataSourceVersion": str(model_payload.get("defaultPowerBIDataSourceVersion", "")),
        "bim.culture": str(model_payload.get("culture", "")),
        "bim.tables": str(table_count),
        "bim.columns": str(column_count),
        "bim.measures": str(measure_count),
        "bim.relationships": str(relationship_count),
    }

    return BimImportBundle(
        concepts=concepts,
        relations=relations,
        metadata={key: value for key, value in metadata.items() if value},
        summary={
            "tables": table_count,
            "columns": column_count,
            "measures": measure_count,
            "relationships": relationship_count,
            "concepts": len(concepts),
            "relations": len(relations),
        },
    )