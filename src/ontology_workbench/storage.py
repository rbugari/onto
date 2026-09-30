from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import Counter
from pathlib import Path

from ontology_workbench.models import DocumentRecord, OntologyProject, ProjectSnapshot, utc_now_iso


class ProjectStore:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def list_project_ids(self) -> list[str]:
        return sorted(file_path.stem for file_path in self.root_dir.glob("*.json"))

    def project_exists(self, project_id: str) -> bool:
        return self._project_path(project_id).exists()

    def load_project(self, project_id: str) -> OntologyProject:
        project_path = self._project_path(project_id)
        if not project_path.exists():
            raise FileNotFoundError(f"Project not found: {project_id}")
        raw = json.loads(project_path.read_text(encoding="utf-8"))
        return OntologyProject.from_dict(raw)

    def save_project(self, project: OntologyProject) -> None:
        project_path = self._project_path(project.id)
        project_path.write_text(
            json.dumps(project.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def create_snapshot(self, project: OntologyProject, note: str = "") -> ProjectSnapshot:
        snapshot_id = self._new_id("snapshot")
        snapshot = ProjectSnapshot(
            snapshot_id=snapshot_id,
            project_id=project.id,
            created_at=utc_now_iso(),
            note=note.strip(),
        )
        snapshot_dir = self._snapshot_dir(project.id)
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "snapshot": snapshot.to_dict(),
            "project": project.to_dict(),
        }
        snapshot_path = snapshot_dir / f"{snapshot.snapshot_id}.json"
        snapshot_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return snapshot

    def list_snapshots(self, project_id: str) -> list[ProjectSnapshot]:
        snapshot_dir = self._snapshot_dir(project_id)
        if not snapshot_dir.exists():
            return []

        snapshots: list[ProjectSnapshot] = []
        for file_path in sorted(snapshot_dir.glob("*.json"), reverse=True):
            raw = json.loads(file_path.read_text(encoding="utf-8"))
            snapshots.append(ProjectSnapshot.from_dict(raw["snapshot"]))
        return snapshots

    def load_snapshot_project(self, project_id: str, snapshot_id: str) -> OntologyProject:
        snapshot_path = self._snapshot_dir(project_id) / f"{snapshot_id}.json"
        if not snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot not found: {project_id}/{snapshot_id}")
        raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
        return OntologyProject.from_dict(raw["project"])

    def save_document(self, project_id: str, filename: str, content: bytes) -> tuple[str, Path]:
        document_id = self.new_document_id()
        target_name = f"{document_id}_{self._safe_document_filename(filename)}"
        target_path = self._documents_dir(project_id) / target_name
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(content)
        return document_id, target_path

    @staticmethod
    def _safe_document_filename(filename: str, max_length: int = 80) -> str:
        original_name = Path(filename).name
        if len(original_name) <= max_length:
            return original_name

        suffix = Path(original_name).suffix
        digest = hashlib.sha256(original_name.encode("utf-8")).hexdigest()[:12]
        stem_length = max_length - len(suffix) - len(digest) - 1
        return f"{Path(original_name).stem[:max(1, stem_length)]}-{digest}{suffix}"
    def save_extracted_text(self, project_id: str, document_id: str, text: str) -> Path:
        target_path = self._extracted_text_dir(project_id) / f"{document_id}.txt"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(text, encoding="utf-8")
        return target_path

    def list_documents(self, project_id: str) -> list[DocumentRecord]:
        manifest_path = self._documents_manifest_path(project_id)
        if not manifest_path.exists():
            return []
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        return [DocumentRecord.from_dict(item) for item in raw]

    def save_documents_manifest(self, project_id: str, documents: list[DocumentRecord]) -> None:
        manifest_path = self._documents_manifest_path(project_id)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps([document.to_dict() for document in documents], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def save_context_chunks(self, project_id: str, chunks: list[dict[str, object]]) -> Path:
        chunks_path = self._context_chunks_path(project_id)
        chunks_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_json(chunks_path, {"chunks": chunks})
        return chunks_path

    def load_context_chunks(self, project_id: str) -> list[dict[str, object]]:
        chunks_path = self._context_chunks_path(project_id)
        if not chunks_path.exists():
            return []
        raw = json.loads(chunks_path.read_text(encoding="utf-8"))
        chunks = raw.get("chunks", [])
        return [dict(chunk) for chunk in chunks if isinstance(chunk, dict)]

    def load_document_text(self, project_id: str, document_id: str) -> str:
        text_path = self._extracted_text_dir(project_id) / f"{document_id}.txt"
        if not text_path.exists():
            return ""
        return text_path.read_text(encoding="utf-8")

    def save_business_context_inventory(self, project_id: str, inventory: dict[str, object]) -> Path:
        inventory_path = self._inventory_path(project_id)
        inventory_path.parent.mkdir(parents=True, exist_ok=True)
        inventory_path.write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")
        return inventory_path

    def load_business_context_inventory(self, project_id: str) -> dict[str, object] | None:
        inventory_path = self._inventory_path(project_id)
        if not inventory_path.exists():
            return None
        return json.loads(inventory_path.read_text(encoding="utf-8"))

    def invalidate_business_context_inventory(self, project_id: str, reason: str) -> None:
        inventory_path = self._inventory_path(project_id)
        if not inventory_path.exists():
            return
        self._write_json(
            inventory_path,
            {
                "status": "invalidated",
                "invalidated_at": utc_now_iso(),
                "reason": reason,
                "message": "El inventario debe regenerarse antes de reutilizarse en Atlas.",
            },
        )

    def new_document_id(self) -> str:
        return self._new_id("document")

    def save_technical_source(
        self, project_id: str, filename: str, content: bytes, source_format: str
    ) -> dict[str, str]:
        """Keep the imported technical artifact locally so an Atlas run can trace it."""
        if not content:
            raise ValueError("Technical source is empty")
        clean_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).name).strip("._") or "source"
        content_sha256 = hashlib.sha256(content).hexdigest()
        target = self._context_project_dir(project_id) / "input" / "technical" / f"{content_sha256[:12]}_{clean_name}"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(content)
        return {
            "source.format": source_format,
            "source.technical.filename": filename,
            "source.technical.path": str(target),
            "source.technical.sha256": content_sha256,
        }

    def save_atlas_assessment(self, package: dict[str, object]) -> Path:
        """Persist an Atlas assessment package in the local workspace convention."""
        manifest = dict(package["manifest"])
        scope = dict(manifest["scope"])
        run_dir = self._atlas_run_dir(
            client_id=str(scope["client_id"]),
            domain_id=str(scope["domain_id"]),
            data_product_id=str(scope["data_product_id"]),
            run_id=str(manifest["run_id"]),
        )
        for name in ("input", "working", "evidence", "review", "publication"):
            (run_dir / name).mkdir(parents=True, exist_ok=True)
        package_dir = run_dir / "output" / "assessment-package"
        package_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(package_dir / "manifest.json", manifest)
        self._write_json(package_dir / "semantic_inventory.json", package["semantic_inventory"])
        self._write_json(
            package_dir / "business_context_inventory.json", package["business_context_inventory"]
        )
        self._write_json(package_dir / "source_inventory.json", package["source_inventory"])
        self._write_json(package_dir / "scope_definition.json", package.get("scope_definition", {}))
        self._write_json(package_dir / "cross_source_map.json", package.get("cross_source_map", {}))
        self._write_json(package_dir / "evidence_index.json", package["evidence_index"])
        self._write_json(package_dir / "readiness_score.json", package["readiness_score"])
        self._write_json(package_dir / "gap_backlog.json", package["gap_backlog"])
        assessment_review = package["assessment_review"]
        self._write_json(package_dir / "assessment_review.json", assessment_review)
        self._write_json(run_dir / "review" / "assessment_review.json", assessment_review)
        (package_dir / "execution_summary.md").write_text(
            str(package["execution_summary"]), encoding="utf-8"
        )
        return package_dir

    def list_atlas_assessments(self, project_id: str) -> list[dict[str, object]]:
        workspace_root = self._workspace_root()
        if not workspace_root.exists():
            return []
        manifests: list[dict[str, object]] = []
        for manifest_path in workspace_root.glob("*/*/*/runs/*/output/assessment-package/manifest.json"):
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            scope = raw.get("scope", {})
            if isinstance(scope, dict) and scope.get("project_id") == project_id:
                raw["package_path"] = str(manifest_path.parent)
                review_path = manifest_path.parent / "assessment_review.json"
                if review_path.exists():
                    raw["assessment_review"] = json.loads(review_path.read_text(encoding="utf-8"))
                manifests.append(raw)
        return sorted(manifests, key=lambda item: str(item.get("created_at", "")), reverse=True)

    def load_atlas_package(self, project_id: str, run_id: str) -> dict[str, object]:
        """Read the artifacts of one Atlas run for inspection in the UI."""
        for assessment in self.list_atlas_assessments(project_id):
            if assessment.get("run_id") != run_id:
                continue
            package_dir = Path(str(assessment["package_path"]))
            package: dict[str, object] = {"manifest": assessment, "package_path": str(package_dir)}
            for name in (
                "scope_definition", "source_inventory", "cross_source_map",
                "readiness_score", "gap_backlog", "assessment_review",
            ):
                package[name] = self._read_json_or_default(package_dir / f"{name}.json", {})
            summary_path = package_dir / "execution_summary.md"
            package["execution_summary"] = summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""
            return package
        raise FileNotFoundError(f"Atlas assessment not found: {run_id}")

    def update_atlas_review(
        self,
        project_id: str,
        run_id: str,
        status: str,
        reviewer: str,
        reviewer_role: str,
        note: str,
    ) -> dict[str, object]:
        allowed_statuses = {"pending_review", "reviewed", "needs_follow_up"}
        if status not in allowed_statuses:
            raise ValueError("Invalid Atlas review status")
        for manifest_path in self._workspace_root().glob("*/*/*/runs/*/output/assessment-package/manifest.json"):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            scope = manifest.get("scope", {})
            if manifest.get("run_id") != run_id or not isinstance(scope, dict) or scope.get("project_id") != project_id:
                continue
            review_path = manifest_path.parent / "assessment_review.json"
            review = json.loads(review_path.read_text(encoding="utf-8"))
            review.update(
                {
                    "status": status,
                    "reviewed_at": utc_now_iso() if status != "pending_review" else None,
                    "reviewer": reviewer.strip(),
                    "reviewer_role": reviewer_role.strip(),
                    "note": note.strip(),
                }
            )
            self._write_json(review_path, review)
            self._write_json(manifest_path.parents[2] / "review" / "assessment_review.json", review)
            return review
        raise FileNotFoundError(f"Atlas assessment not found: {run_id}")

    def save_nexo_draft(self, draft: dict[str, object]) -> Path:
        manifest = dict(draft["manifest"])
        project_id = str(manifest["project_id"])
        draft_id = str(manifest["draft_id"])
        draft_dir = self._nexo_draft_dir(project_id, draft_id)
        for name in ("input", "working", "review", "output"):
            (draft_dir / name).mkdir(parents=True, exist_ok=True)
        self._write_json(draft_dir / "draft_manifest.json", manifest)
        self._write_json(draft_dir / "working" / "candidates.json", draft["candidates"])
        self._write_json(draft_dir / "review" / "review_decisions.json", draft["review_decisions"])
        self._write_json(draft_dir / "working" / "model_elements.json", draft.get("model_elements", []))
        self._write_json(
            draft_dir / "review" / "model_element_decisions.json",
            draft.get("model_element_decisions", []),
        )
        return draft_dir

    def list_nexo_drafts(self, project_id: str) -> list[dict[str, object]]:
        drafts: list[dict[str, object]] = []
        root = self._nexo_project_root(project_id) / "drafts"
        if not root.exists():
            return []
        for manifest_path in root.glob("*/draft_manifest.json"):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["draft_path"] = str(manifest_path.parent)
            drafts.append(manifest)
        return sorted(drafts, key=lambda item: str(item.get("created_at", "")), reverse=True)

    def load_nexo_draft(self, project_id: str, draft_id: str) -> dict[str, object]:
        draft_dir = self._nexo_draft_dir(project_id, draft_id)
        manifest_path = draft_dir / "draft_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Nexo draft not found: {draft_id}")
        return {
            "manifest": json.loads(manifest_path.read_text(encoding="utf-8")),
            "candidates": json.loads((draft_dir / "working" / "candidates.json").read_text(encoding="utf-8")),
            "review_decisions": json.loads((draft_dir / "review" / "review_decisions.json").read_text(encoding="utf-8")),
            "model_elements": self._read_json_or_default(draft_dir / "working" / "model_elements.json", []),
            "model_element_decisions": self._read_json_or_default(
                draft_dir / "review" / "model_element_decisions.json", []
            ),
            "draft_path": str(draft_dir),
        }

    def update_nexo_candidate(
        self,
        project_id: str,
        draft_id: str,
        candidate_id: str,
        status: str,
        reviewer: str,
        reviewer_role: str,
        note: str,
    ) -> dict[str, object]:
        if status not in {"approved", "rejected", "pending_review"}:
            raise ValueError("Invalid Nexo candidate status")
        draft = self.load_nexo_draft(project_id, draft_id)
        candidates = list(draft["candidates"])
        candidate = next((item for item in candidates if item.get("candidate_id") == candidate_id), None)
        if candidate is None:
            raise FileNotFoundError(f"Nexo candidate not found: {candidate_id}")
        decision = {
            "decision_id": self._new_id("decision"),
            "candidate_id": candidate_id,
            "status": status,
            "reviewer": reviewer.strip(),
            "reviewer_role": reviewer_role.strip(),
            "note": note.strip(),
            "decided_at": utc_now_iso(),
        }
        candidate["status"] = status
        candidate["decision"] = decision
        decisions = list(draft["review_decisions"])
        decisions.append(decision)
        draft_dir = self._nexo_draft_dir(project_id, draft_id)
        status_counts = Counter(str(item.get("status", "pending_review")) for item in candidates)
        type_counts = Counter(str(item.get("candidate_type", "unknown")) for item in candidates)
        manifest = dict(draft["manifest"])
        manifest["candidate_summary"] = {
            "total": len(candidates),
            "pending_review": status_counts["pending_review"],
            "approved": status_counts["approved"],
            "rejected": status_counts["rejected"],
            **dict(type_counts),
        }
        self._write_json(draft_dir / "draft_manifest.json", manifest)
        self._write_json(draft_dir / "working" / "candidates.json", candidates)
        self._write_json(draft_dir / "review" / "review_decisions.json", decisions)
        return candidate

    def bulk_update_nexo_candidates(
        self,
        project_id: str,
        draft_id: str,
        candidate_ids: list[str],
        status: str,
        reviewer: str,
        reviewer_role: str,
        note: str,
    ) -> dict[str, int]:
        if status not in {"approved", "rejected"}:
            raise ValueError("Bulk Nexo decisions must be approved or rejected")
        selected_ids = list(dict.fromkeys(candidate_ids))
        if not selected_ids:
            raise ValueError("Select at least one Nexo candidate")
        draft = self.load_nexo_draft(project_id, draft_id)
        candidates = list(draft["candidates"])
        by_id = {str(candidate["candidate_id"]): candidate for candidate in candidates}
        missing_ids = [candidate_id for candidate_id in selected_ids if candidate_id not in by_id]
        if missing_ids:
            raise FileNotFoundError(f"Nexo candidates not found: {', '.join(missing_ids)}")
        decisions = list(draft["review_decisions"])
        for candidate_id in selected_ids:
            decision = {
                "decision_id": self._new_id("decision"),
                "candidate_id": candidate_id,
                "status": status,
                "reviewer": reviewer.strip(),
                "reviewer_role": reviewer_role.strip(),
                "note": note.strip(),
                "decided_at": utc_now_iso(),
                "decision_mode": "bulk_review",
            }
            by_id[candidate_id]["status"] = status
            by_id[candidate_id]["decision"] = decision
            decisions.append(decision)
        self._save_nexo_candidate_state(project_id, draft_id, draft, candidates, decisions)
        return {"updated": len(selected_ids)}

    def add_nexo_model_element(
        self, project_id: str, draft_id: str, element: dict[str, object]
    ) -> dict[str, object]:
        draft = self.load_nexo_draft(project_id, draft_id)
        candidates = {str(item["candidate_id"]) for item in draft["candidates"]}
        linked_ids = [str(item) for item in element.get("linked_candidate_ids", [])]
        unknown_ids = [candidate_id for candidate_id in linked_ids if candidate_id not in candidates]
        if unknown_ids:
            raise ValueError("Los vínculos del modelo deben apuntar a candidatos del draft")
        elements = list(draft["model_elements"])
        elements.append(element)
        self._save_nexo_model_element_state(
            project_id, draft_id, draft, elements, list(draft["model_element_decisions"])
        )
        return element

    def update_nexo_model_element(
        self,
        project_id: str,
        draft_id: str,
        element_id: str,
        status: str,
        reviewer: str,
        reviewer_role: str,
        note: str,
    ) -> dict[str, object]:
        if status not in {"approved", "rejected", "pending_review"}:
            raise ValueError("Invalid Nexo model element status")
        draft = self.load_nexo_draft(project_id, draft_id)
        elements = list(draft["model_elements"])
        element = next((item for item in elements if item.get("element_id") == element_id), None)
        if element is None:
            raise FileNotFoundError(f"Nexo model element not found: {element_id}")
        decision = {
            "decision_id": self._new_id("model-decision"),
            "element_id": element_id,
            "status": status,
            "reviewer": reviewer.strip(),
            "reviewer_role": reviewer_role.strip(),
            "note": note.strip(),
            "decided_at": utc_now_iso(),
        }
        element["status"] = status
        element["decision"] = decision
        decisions = list(draft["model_element_decisions"])
        decisions.append(decision)
        self._save_nexo_model_element_state(project_id, draft_id, draft, elements, decisions)
        return element

    def save_nexo_consolidation_suggestions(
        self, project_id: str, draft_id: str, suggestions: dict[str, object]
    ) -> None:
        draft_dir = self._nexo_draft_dir(project_id, draft_id)
        if not (draft_dir / "draft_manifest.json").exists():
            raise FileNotFoundError(f"Nexo draft not found: {draft_id}")
        self._write_json(draft_dir / "working" / "consolidation_suggestions.json", suggestions)
        decisions_path = draft_dir / "review" / "consolidation_decisions.json"
        if not decisions_path.exists():
            self._write_json(decisions_path, [])

    def load_nexo_consolidation_suggestions(
        self, project_id: str, draft_id: str
    ) -> dict[str, object] | None:
        path = self._nexo_draft_dir(project_id, draft_id) / "working" / "consolidation_suggestions.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def update_nexo_consolidation_suggestion(
        self,
        project_id: str,
        draft_id: str,
        suggestion_id: str,
        status: str,
        reviewer: str,
        note: str,
    ) -> dict[str, object]:
        if status not in {"pending_review", "accepted_as_review_plan", "rejected", "applied"}:
            raise ValueError("Invalid Nexo consolidation suggestion status")
        package = self.load_nexo_consolidation_suggestions(project_id, draft_id)
        if package is None:
            raise FileNotFoundError("No Nexo consolidation suggestions found")
        suggestions = list(package["suggestions"])
        suggestion = next((item for item in suggestions if item.get("suggestion_id") == suggestion_id), None)
        if suggestion is None:
            raise FileNotFoundError(f"Nexo consolidation suggestion not found: {suggestion_id}")
        decision = {
            "decision_id": self._new_id("consolidation-decision"),
            "suggestion_id": suggestion_id,
            "status": status,
            "reviewer": reviewer.strip(),
            "note": note.strip(),
            "decided_at": utc_now_iso(),
        }
        suggestion["status"] = status
        suggestion["decision"] = decision
        draft_dir = self._nexo_draft_dir(project_id, draft_id)
        self._write_json(draft_dir / "working" / "consolidation_suggestions.json", package)
        decisions_path = draft_dir / "review" / "consolidation_decisions.json"
        decisions = json.loads(decisions_path.read_text(encoding="utf-8")) if decisions_path.exists() else []
        decisions.append(decision)
        self._write_json(decisions_path, decisions)
        return suggestion

    def apply_nexo_consolidation_suggestion(
        self, project_id: str, draft_id: str, suggestion_id: str, reviewer: str, note: str
    ) -> dict[str, object]:
        package = self.load_nexo_consolidation_suggestions(project_id, draft_id)
        if package is None:
            raise FileNotFoundError("No Nexo consolidation suggestions found")
        suggestions = list(package["suggestions"])
        suggestion = next((item for item in suggestions if item.get("suggestion_id") == suggestion_id), None)
        if suggestion is None:
            raise FileNotFoundError(f"Nexo consolidation suggestion not found: {suggestion_id}")
        if suggestion.get("status") != "accepted_as_review_plan":
            raise ValueError("Only an accepted consolidation review plan can be applied")
        draft = self.load_nexo_draft(project_id, draft_id)
        candidates = list(draft["candidates"])
        by_id = {str(candidate["candidate_id"]): candidate for candidate in candidates}
        canonical_id = str(suggestion["canonical_candidate_id"])
        duplicate_ids = [str(item) for item in suggestion["duplicate_candidate_ids"]]
        if canonical_id not in by_id or by_id[canonical_id].get("status") == "rejected":
            raise ValueError("The canonical candidate must exist and cannot be rejected")
        invalid_duplicates = [
            candidate_id for candidate_id in duplicate_ids
            if candidate_id not in by_id or by_id[candidate_id].get("status") != "pending_review"
        ]
        if invalid_duplicates:
            raise ValueError("Only pending duplicate candidates can be consolidated")
        decisions = list(draft["review_decisions"])
        for candidate_id in duplicate_ids:
            decision = {
                "decision_id": self._new_id("decision"),
                "candidate_id": candidate_id,
                "status": "rejected",
                "reviewer": reviewer.strip(),
                "reviewer_role": "consolidation_reviewer",
                "note": f"Consolidated into {canonical_id}. {note.strip()}".strip(),
                "decided_at": utc_now_iso(),
                "decision_mode": "consolidation_application",
            }
            by_id[candidate_id]["status"] = "rejected"
            by_id[candidate_id]["decision"] = decision
            decisions.append(decision)
        self._save_nexo_candidate_state(project_id, draft_id, draft, candidates, decisions)
        consolidation_decision = {
            "decision_id": self._new_id("consolidation-decision"),
            "suggestion_id": suggestion_id,
            "status": "applied",
            "reviewer": reviewer.strip(),
            "note": note.strip(),
            "decided_at": utc_now_iso(),
        }
        suggestion["status"] = "applied"
        suggestion["decision"] = consolidation_decision
        draft_dir = self._nexo_draft_dir(project_id, draft_id)
        self._write_json(draft_dir / "working" / "consolidation_suggestions.json", package)
        decisions_path = draft_dir / "review" / "consolidation_decisions.json"
        consolidation_decisions = json.loads(decisions_path.read_text(encoding="utf-8")) if decisions_path.exists() else []
        consolidation_decisions.append(consolidation_decision)
        self._write_json(decisions_path, consolidation_decisions)
        return {"canonical_candidate_id": canonical_id, "rejected_duplicates": len(duplicate_ids)}

    def save_nexo_release(self, project_id: str, release: dict[str, object]) -> Path:
        manifest = dict(release["manifest"])
        release_dir = self._nexo_project_root(project_id) / "releases" / self._safe_workspace_segment(str(manifest["release_id"]))
        if release_dir.exists():
            raise ValueError(f"Nexo release already exists: {manifest['release_id']}")
        package_dir = release_dir / "ontology-release"
        package_dir.mkdir(parents=True, exist_ok=False)
        self._write_json(package_dir / "release_manifest.json", manifest)
        self._write_json(package_dir / "canonical_ontology.json", release["canonical_ontology"])
        self._write_json(package_dir / "review_decisions.json", release["review_decisions"])
        self._write_json(package_dir / "evidence_index.json", release["evidence_index"])
        self._write_json(package_dir / "source_bindings.json", release["source_bindings"])
        self._write_json(package_dir / "agent_context_pack.json", release["agent_context_pack"])
        self._write_json(package_dir / "interoperability_mappings.json", release["interoperability_mappings"])
        (package_dir / "publication_packages").mkdir()
        return package_dir

    def list_nexo_releases(self, project_id: str) -> list[dict[str, object]]:
        releases = []
        for manifest_path in (self._nexo_project_root(project_id) / "releases").glob("*/ontology-release/release_manifest.json"):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["package_path"] = str(manifest_path.parent)
            releases.append(manifest)
        return sorted(releases, key=lambda item: str(item.get("created_at", "")), reverse=True)

    def load_nexo_release(self, project_id: str, release_id: str) -> dict[str, object]:
        package_dir = (
            self._nexo_project_root(project_id)
            / "releases"
            / self._safe_workspace_segment(release_id)
            / "ontology-release"
        )
        manifest_path = package_dir / "release_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Nexo release not found: {release_id}")
        return {
            "manifest": json.loads(manifest_path.read_text(encoding="utf-8")),
            "canonical_ontology": json.loads(
                (package_dir / "canonical_ontology.json").read_text(encoding="utf-8")
            ),
            "package_path": str(package_dir),
        }

    def save_nexo_comparison(self, project_id: str, comparison: dict[str, object]) -> Path:
        references = (dict(comparison["baseline"]), dict(comparison["candidate"]))
        comparison_id = "comparison-" + "-to-".join(
            self._safe_workspace_segment(str(reference["id"])) for reference in references
        )
        comparison_dir = self._nexo_project_root(project_id) / "comparisons"
        comparison_dir.mkdir(parents=True, exist_ok=True)
        path = comparison_dir / f"{comparison_id}.json"
        self._write_json(path, comparison)
        return path

    def save_interoperability_package(
        self, project_id: str, package: dict[str, object]
    ) -> Path:
        manifest = dict(package["manifest"])
        package_dir = (
            self.root_dir.parent
            / "interoperability"
            / self._safe_workspace_segment(project_id)
            / self._safe_workspace_segment(str(manifest["release_id"]))
            / self._safe_workspace_segment(str(manifest["target"]))
            / self._safe_workspace_segment(str(manifest["package_id"]))
        )
        package_dir.mkdir(parents=True, exist_ok=False)
        self._write_json(package_dir / "publication_manifest.json", manifest)
        self._write_json(package_dir / "mapping.json", package["mapping"])
        self._write_json(package_dir / "deployment_manifest.json", package["deployment_manifest"])
        return package_dir

    def save_fabric_discovery(self, project_id: str, discovery_id: str, payload: dict[str, object]) -> Path:
        discovery_dir = (
            self.root_dir.parent
            / "fabric"
            / self._safe_workspace_segment(project_id)
            / "discoveries"
            / self._safe_workspace_segment(discovery_id)
        )
        discovery_dir.mkdir(parents=True, exist_ok=False)
        self._write_json(discovery_dir / "metadata_inventory.json", payload)
        return discovery_dir

    def save_runtime_investigation(self, project_id: str, investigation: dict[str, object]) -> Path:
        manifest = dict(investigation["manifest"])
        run_dir = self.root_dir.parent / "runtime" / self._safe_workspace_segment(project_id) / self._safe_workspace_segment(str(manifest["release_id"])) / self._safe_workspace_segment(str(manifest["investigation_id"]))
        run_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(run_dir / "investigation_manifest.json", manifest)
        self._write_json(run_dir / "request.json", investigation["request"])
        self._write_json(run_dir / "retrieval.json", investigation["retrieval"])
        live_query = investigation.get("live_query", {})
        if not isinstance(live_query, dict):
            live_query = {}
        request = investigation.get("request", {})
        question = str(request.get("question", "")) if isinstance(request, dict) else ""
        self._write_json(
            run_dir / "traceability.json",
            {
                "reasoning_advisory": investigation.get("reasoning_advisory", {}),
                "live_query": live_query,
                "llm_used": investigation.get("llm_used", False),
                "llm_plan": investigation.get("llm_plan", {}),
                "llm_response": investigation.get("llm_response", {}),
            },
        )
        self._write_json(
            run_dir / "audit.json",
            {
                "event_type": "argos_investigation",
                "project_id": project_id,
                "release_id": manifest.get("release_id", ""),
                "investigation_id": manifest.get("investigation_id", ""),
                "created_at": manifest.get("created_at", ""),
                "actor": "local-user",
                "status": manifest.get("status", ""),
                "question_sha256": hashlib.sha256(question.encode("utf-8")).hexdigest(),
                "llm_used": bool(investigation.get("llm_used", False)),
                "query_name": live_query.get("query_name", ""),
                "operation": live_query.get("operation", ""),
                "adapter_status": live_query.get("status", ""),
                "row_count": len(live_query.get("rows", [])) if isinstance(live_query.get("rows", []), list) else 0,
                "secrets_persisted": False,
            },
        )
        (run_dir / "answer.md").write_text(str(investigation["answer"]), encoding="utf-8")
        return run_dir

    def list_runtime_investigations(
        self, project_id: str, release_id: str
    ) -> list[dict[str, object]]:
        runtime_dir = (
            self.root_dir.parent
            / "runtime"
            / self._safe_workspace_segment(project_id)
            / self._safe_workspace_segment(release_id)
        )
        if not runtime_dir.exists():
            return []
        investigations = []
        for manifest_path in runtime_dir.glob("*/investigation_manifest.json"):
            investigations.append(json.loads(manifest_path.read_text(encoding="utf-8")))
        return sorted(
            investigations,
            key=lambda manifest: str(manifest.get("created_at", "")),
            reverse=True,
        )

    def runtime_retention_report(
        self, project_id: str, release_id: str, keep_latest: int = 100
    ) -> dict[str, object]:
        if keep_latest < 0:
            raise ValueError("keep_latest no puede ser negativo")
        investigations = self.list_runtime_investigations(project_id, release_id)
        retained = investigations[:keep_latest]
        candidates = investigations[keep_latest:]
        return {
            "project_id": project_id,
            "release_id": release_id,
            "policy": "manual_review",
            "keep_latest": keep_latest,
            "total_investigations": len(investigations),
            "retained_ids": [str(item.get("investigation_id", "")) for item in retained],
            "candidate_ids": [str(item.get("investigation_id", "")) for item in candidates],
            "deletion_performed": False,
        }

    def load_runtime_investigation(
        self, project_id: str, release_id: str, investigation_id: str
    ) -> dict[str, object]:
        run_dir = (
            self.root_dir.parent
            / "runtime"
            / self._safe_workspace_segment(project_id)
            / self._safe_workspace_segment(release_id)
            / self._safe_workspace_segment(investigation_id)
        )
        return {
            "manifest": json.loads((run_dir / "investigation_manifest.json").read_text(encoding="utf-8")),
            "request": json.loads((run_dir / "request.json").read_text(encoding="utf-8")),
            "retrieval": json.loads((run_dir / "retrieval.json").read_text(encoding="utf-8")),
            "audit": json.loads((run_dir / "audit.json").read_text(encoding="utf-8")),
            **json.loads((run_dir / "traceability.json").read_text(encoding="utf-8")),
            "answer": (run_dir / "answer.md").read_text(encoding="utf-8"),
            "package_path": str(run_dir),
        }

    def save_runtime_evaluation(self, project_id: str, evaluation: dict[str, object]) -> Path:
        manifest = dict(evaluation["manifest"])
        evaluation_dir = (
            self.root_dir.parent
            / "runtime"
            / self._safe_workspace_segment(project_id)
            / self._safe_workspace_segment(str(manifest["release_id"]))
            / "evaluations"
            / self._safe_workspace_segment(str(manifest["evaluation_id"]))
        )
        evaluation_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(evaluation_dir / "evaluation_manifest.json", manifest)
        self._write_json(evaluation_dir / "summary.json", evaluation["summary"])
        self._write_json(evaluation_dir / "cases.json", evaluation["cases"])
        return evaluation_dir

    def _project_path(self, project_id: str) -> Path:
        return self.root_dir / f"{project_id}.json"

    def _snapshot_dir(self, project_id: str) -> Path:
        return self.root_dir.parent / "history" / project_id

    def _context_project_dir(self, project_id: str) -> Path:
        return self.root_dir.parent / "context" / project_id

    def _documents_dir(self, project_id: str) -> Path:
        return self._context_project_dir(project_id) / "input" / "documentation"

    def _extracted_text_dir(self, project_id: str) -> Path:
        return self._context_project_dir(project_id) / "working" / "extracted_text"

    def _documents_manifest_path(self, project_id: str) -> Path:
        return self._context_project_dir(project_id) / "working" / "documents_manifest.json"

    def _inventory_path(self, project_id: str) -> Path:
        return self._context_project_dir(project_id) / "output" / "business_context_inventory.json"

    def _context_chunks_path(self, project_id: str) -> Path:
        return self._context_project_dir(project_id) / "working" / "chunks" / "chunks.json"

    def _workspace_root(self) -> Path:
        return self.root_dir.parent / "workspaces"

    def _nexo_project_root(self, project_id: str) -> Path:
        return self.root_dir.parent / "registry" / self._safe_workspace_segment(project_id)

    def _nexo_draft_dir(self, project_id: str, draft_id: str) -> Path:
        return self._nexo_project_root(project_id) / "drafts" / self._safe_workspace_segment(draft_id)

    def _save_nexo_candidate_state(
        self,
        project_id: str,
        draft_id: str,
        draft: dict[str, object],
        candidates: list[dict[str, object]],
        decisions: list[dict[str, object]],
    ) -> None:
        status_counts = Counter(str(item.get("status", "pending_review")) for item in candidates)
        type_counts = Counter(str(item.get("candidate_type", "unknown")) for item in candidates)
        manifest = dict(draft["manifest"])
        manifest["candidate_summary"] = {
            "total": len(candidates),
            "pending_review": status_counts["pending_review"],
            "approved": status_counts["approved"],
            "rejected": status_counts["rejected"],
            **dict(type_counts),
        }
        draft_dir = self._nexo_draft_dir(project_id, draft_id)
        self._write_json(draft_dir / "draft_manifest.json", manifest)
        self._write_json(draft_dir / "working" / "candidates.json", candidates)
        self._write_json(draft_dir / "review" / "review_decisions.json", decisions)

    def _save_nexo_model_element_state(
        self,
        project_id: str,
        draft_id: str,
        draft: dict[str, object],
        elements: list[dict[str, object]],
        decisions: list[dict[str, object]],
    ) -> None:
        status_counts = Counter(str(item.get("status", "pending_review")) for item in elements)
        type_counts = Counter(str(item.get("element_type", "unknown")) for item in elements)
        manifest = dict(draft["manifest"])
        manifest["model_element_summary"] = {
            "total": len(elements),
            "pending_review": status_counts["pending_review"],
            "approved": status_counts["approved"],
            "rejected": status_counts["rejected"],
            **dict(type_counts),
        }
        draft_dir = self._nexo_draft_dir(project_id, draft_id)
        self._write_json(draft_dir / "draft_manifest.json", manifest)
        self._write_json(draft_dir / "working" / "model_elements.json", elements)
        self._write_json(draft_dir / "review" / "model_element_decisions.json", decisions)

    def _atlas_run_dir(
        self, client_id: str, domain_id: str, data_product_id: str, run_id: str
    ) -> Path:
        return (
            self._workspace_root()
            / self._safe_workspace_segment(client_id)
            / self._safe_workspace_segment(domain_id)
            / self._safe_workspace_segment(data_product_id)
            / "runs"
            / self._safe_workspace_segment(run_id)
        )

    def _new_id(self, prefix: str) -> str:
        return f"{prefix}-{utc_now_iso().replace(':', '-').replace('+', '-')}-{uuid.uuid4().hex[:12]}"

    def _safe_workspace_segment(self, value: str) -> str:
        clean_value = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
        if not clean_value:
            raise ValueError("Workspace identifiers must contain letters or digits")
        return clean_value

    def _write_json(self, path: Path, payload: object) -> None:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _read_json_or_default(self, path: Path, default: object) -> object:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def unique_file_paths_by_content(paths: list[Path]) -> list[Path]:
    """Keep the first path for each content hash, preserving sorted input order."""
    seen_hashes: set[str] = set()
    unique_paths: list[Path] = []
    for path in paths:
        content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)
        unique_paths.append(path)
    return unique_paths
