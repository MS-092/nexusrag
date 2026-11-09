from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_WEB_ORIGIN = "http://localhost:3000"


def _default_data_dir() -> Path:
    # <repo>/data, next to api/ and web/. One local folder holds everything.
    return Path(__file__).resolve().parents[2] / "data"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    web_origin: str = DEFAULT_WEB_ORIGIN
    max_upload_bytes: int = 50 * 1024 * 1024

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            data_dir=Path(os.environ.get("NEXUSRAG_DATA_DIR") or _default_data_dir()),
            web_origin=os.environ.get("NEXUSRAG_WEB_ORIGIN", DEFAULT_WEB_ORIGIN),
        )
