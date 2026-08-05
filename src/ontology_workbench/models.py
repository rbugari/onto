from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class Concept:
    id: str
    name: str
    definition: str = ""
    status: str = "draft"
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "Concept":
        return cls(
            id=str(raw["id"]),
            name=str(raw["name"]),
            definition=str(raw.get("definition", "")),
            status=str(raw.get("status", "draft")),
            tags=[str(item) for item in raw.get("tags", [])],
            metadata={
                str(key): str(value) for key, value in dict(raw.get("metadata", {})).items()
            },
        )


@dataclass(slots=True)
class Relation:
    id: str
    source_id: str
    target_id: str
    relation_type: str
    description: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "Relation":
        return cls(
            id=str(raw["id"]),
            source_id=str(raw["source_id"]),
            target_id=str(raw["target_id"]),
            relation_type=str(raw["relation_type"]),
            description=str(raw.get("description", "")),
        )


@dataclass(slots=True)
class OntologyProject:
    id: str
    name: str
    description: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    concepts: list[Concept] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "concepts": [concept.to_dict() for concept in self.concepts],
            "relations": [relation.to_dict() for relation in self.relations],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "OntologyProject":
        return cls(
            id=str(raw["id"]),
            name=str(raw["name"]),
            description=str(raw.get("description", "")),
            created_at=str(raw.get("created_at", utc_now_iso())),
            updated_at=str(raw.get("updated_at", utc_now_iso())),
            concepts=[Concept.from_dict(item) for item in raw.get("concepts", [])],
            relations=[Relation.from_dict(item) for item in raw.get("relations", [])],
            metadata={
                str(key): str(value) for key, value in dict(raw.get("metadata", {})).items()
            },
        )


@dataclass(slots=True)
class ProjectSnapshot:
    snapshot_id: str
    project_id: str
    created_at: str
    note: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "ProjectSnapshot":
        return cls(
            snapshot_id=str(raw["snapshot_id"]),
            project_id=str(raw["project_id"]),
            created_at=str(raw["created_at"]),
            note=str(raw.get("note", "")),
        )


@dataclass(slots=True)
class ValidationIssue:
    level: str
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(slots=True)
class DocumentRecord:
    document_id: str
    project_id: str
    filename: str
    stored_path: str
    doc_type: str
    content_type: str
    uploaded_at: str
    extraction_status: str
    extracted_text_path: str = ""
    extracted_chars: int = 0
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "DocumentRecord":
        return cls(
            document_id=str(raw["document_id"]),
            project_id=str(raw["project_id"]),
            filename=str(raw["filename"]),
            stored_path=str(raw["stored_path"]),
            doc_type=str(raw.get("doc_type", "misc")),
            content_type=str(raw.get("content_type", "application/octet-stream")),
            uploaded_at=str(raw.get("uploaded_at", utc_now_iso())),
            extraction_status=str(raw.get("extraction_status", "pending")),
            extracted_text_path=str(raw.get("extracted_text_path", "")),
            extracted_chars=int(raw.get("extracted_chars", 0)),
            notes=str(raw.get("notes", "")),
        )
