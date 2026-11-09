"""Extractor interface: one function per Source kind, returning positioned text blocks.

A block is {"text": str, "position": dict}. Position is {"page": n} for PDFs,
{"sheet": s, "rows": [a, b]} for spreadsheets, {} for images and notes.
Retrieval never sees anything but blocks, so a stronger Extractor (for example
Unlimited-OCR) can replace one here without touching the index.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

Block = dict
Extractor = Callable[[Path], list[Block]]


class ExtractionError(Exception):
    """Raised with a message that is safe to show to the user."""


EXTRACTORS: dict[str, Extractor] = {}
EXTENSIONS: dict[str, str] = {}  # ".pdf" -> "pdf"


def register(kind: str, extensions: tuple[str, ...], fn: Extractor) -> None:
    EXTRACTORS[kind] = fn
    for ext in extensions:
        EXTENSIONS[ext] = kind


def kind_for(filename: str) -> str | None:
    return EXTENSIONS.get(Path(filename).suffix.lower())


def accepted_extensions() -> list[str]:
    return sorted(EXTENSIONS)


def extract(kind: str, path: Path) -> list[Block]:
    return EXTRACTORS[kind](path)


from nexusrag.extractors import pdf  # noqa: E402,F401  (registers itself)
