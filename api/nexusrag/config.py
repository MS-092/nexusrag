from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_WEB_ORIGIN = "http://localhost:3000"


def _default_data_dir() -> Path:
    # <repo>/data, next to api/ and web/. One local folder holds everything.
    return Path(__file__).resolve().parents[2] / "data"


def _default_skills_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "skills"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    web_origin: str = DEFAULT_WEB_ORIGIN
    max_upload_bytes: int = 50 * 1024 * 1024
    skills_dir: Path = field(default_factory=_default_skills_dir)

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            data_dir=Path(os.environ.get("NEXUSRAG_DATA_DIR") or _default_data_dir()),
            web_origin=os.environ.get("NEXUSRAG_WEB_ORIGIN", DEFAULT_WEB_ORIGIN),
            skills_dir=Path(os.environ.get("NEXUSRAG_SKILLS_DIR") or _default_skills_dir()),
        )
