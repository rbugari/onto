"""Generate Nexo consolidation suggestions in a background-safe local process."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ontology_workbench.models import utc_now_iso
from ontology_workbench.service import WorkbenchService
from ontology_workbench.storage import ProjectStore


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: run_nexo_consolidation.py <project_id> <draft_id>")
    project_id, draft_id = sys.argv[1:]
    status_path = ROOT_DIR / "data" / "registry" / project_id / "drafts" / draft_id / "working" / "consolidation_status.json"
    status_path.write_text(
        json.dumps({"status": "running", "started_at": utc_now_iso()}, indent=2), encoding="utf-8"
    )
    service = WorkbenchService(ProjectStore(ROOT_DIR / "data" / "projects"))
    try:
        package = service.generate_nexo_consolidation_suggestions(project_id, draft_id)
        result = {
            "status": "completed",
            "completed_at": utc_now_iso(),
            "mode": package["mode"],
            "suggestions": len(package["suggestions"]),
            "warning": package.get("warning", ""),
        }
    except Exception as exc:
        result = {
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
