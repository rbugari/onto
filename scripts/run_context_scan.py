"""Run a potentially long local context scan without tying it to a terminal timeout."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ontology_workbench.service import WorkbenchService
from ontology_workbench.storage import ProjectStore
from ontology_workbench.models import utc_now_iso


def main() -> None:
    project_id = sys.argv[1] if len(sys.argv) > 1 else "fabric-gold-sic-risk-pilot"
    status_path = ROOT_DIR / "data" / "context" / project_id / "working" / "llm_scan_status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(
        json.dumps({"project_id": project_id, "status": "running", "started_at": utc_now_iso()}, indent=2),
        encoding="utf-8",
    )
    service = WorkbenchService(ProjectStore(ROOT_DIR / "data" / "projects"))
    try:
        inventory = service.scan_business_context(project_id)
        result = {
            "project_id": project_id,
            "status": "completed",
            "completed_at": utc_now_iso(),
            "scan_mode": inventory.get("scan_mode"),
            "definitions": len(inventory.get("definitions", [])),
            "business_rules": len(inventory.get("business_rules", [])),
            "kpis": len(inventory.get("kpis", [])),
            "scanner_warning": inventory.get("scanner_warning", ""),
        }
    except Exception as exc:
        result = {
            "project_id": project_id,
            "status": "failed",
            "completed_at": utc_now_iso(),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        status_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        raise
    status_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
