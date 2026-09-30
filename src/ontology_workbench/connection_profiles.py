from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


_PROFILE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_ALLOWED_KEYS = {
    "DB_HOST",
    "DB_PORT",
    "DB_USER",
    "DB_PASSWORD",
    "DB_NAME",
}


class ConnectionProfileError(ValueError):
    """Controlled error for invalid or missing project connection profiles."""


@dataclass(frozen=True)
class ConnectionProfileSummary:
    project_id: str
    profile_id: str
    adapter: str
    path: Path


class ConnectionProfileStore:
    """Keep connection secrets outside project JSON, grouped by project and profile."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir)

    def profile_path(self, project_id: str, profile_id: str) -> Path:
        clean_project_id = _safe_id(project_id, "project_id")
        clean_profile_id = _safe_id(profile_id, "profile_id")
        return self.root_dir / clean_project_id / f"{clean_profile_id}.env"

    def save_mariadb_profile(
        self,
        project_id: str,
        profile_id: str,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
    ) -> ConnectionProfileSummary:
        if not host.strip() or not user.strip() or not password or not database.strip():
            raise ConnectionProfileError(
                "MariaDB requiere host, usuario, password y base de datos"
            )
        if not 1 <= port <= 65_535:
            raise ConnectionProfileError("El puerto MariaDB esta fuera de rango")
        path = self.profile_path(project_id, profile_id)
        values = {
            "ONTO_CONNECTION_ADAPTER": "mariadb",
            "ONTO_CONNECTION_PROFILE_ID": profile_id,
            "DB_HOST": host.strip(),
            "DB_PORT": str(port),
            "DB_USER": user.strip(),
            "DB_PASSWORD": password,
            "DB_NAME": database.strip(),
        }
        if any("\n" in value or "\r" in value for value in values.values()):
            raise ConnectionProfileError("Los valores de conexion no pueden contener saltos de linea")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(f"{key}={_quote_env_value(value)}\n" for key, value in values.items()),
            encoding="utf-8",
        )
        try:
            path.chmod(0o600)
        except OSError:
            pass
        return ConnectionProfileSummary(project_id, profile_id, "mariadb", path)

    def load(self, project_id: str, profile_id: str) -> dict[str, str]:
        path = self.profile_path(project_id, profile_id)
        if not path.exists():
            raise ConnectionProfileError(
                f"No existe el perfil de conexion '{profile_id}' para el proyecto '{project_id}'"
            )
        raw = dotenv_values(path)
        return {str(key): str(value) for key, value in raw.items() if value is not None}

    def list(self, project_id: str) -> list[ConnectionProfileSummary]:
        project_dir = self.root_dir / _safe_id(project_id, "project_id")
        if not project_dir.exists():
            return []
        summaries: list[ConnectionProfileSummary] = []
        for path in sorted(project_dir.glob("*.env")):
            values = dotenv_values(path)
            summaries.append(
                ConnectionProfileSummary(
                    project_id=project_id,
                    profile_id=path.stem,
                    adapter=str(values.get("ONTO_CONNECTION_ADAPTER", "unknown")),
                    path=path,
                )
            )
        return summaries


def _safe_id(value: str, label: str) -> str:
    clean = value.strip()
    if not _PROFILE_ID_RE.fullmatch(clean):
        raise ConnectionProfileError(f"{label} contiene caracteres no permitidos")
    return clean


def _quote_env_value(value: str) -> str:
    if not value or any(character in value for character in " #\t"):
        return '"' + value.replace('"', '\\"') + '"'
    return value
