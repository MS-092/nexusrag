from __future__ import annotations

import re
from pathlib import Path

from nexusrag.extractors import Block, ExtractionError, register


def extract_note(path: Path) -> list[Block]:
    """A Note is Markdown written in the app. Split at headings so each
    section chunks cleanly; the text itself is kept verbatim."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ExtractionError("This note is empty.")
    sections = [s.strip() for s in re.split(r"(?m)^(?=#{1,6}\s)", text) if s.strip()]
    return [{"text": s, "position": {}} for s in sections]


# No file extensions: Notes are created in the app, never uploaded.
register("note", (), extract_note)
