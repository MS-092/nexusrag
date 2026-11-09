from __future__ import annotations

import threading
from pathlib import Path

import pymupdf

from nexusrag.extractors import Block, ExtractionError, register

_engine = None
_lock = threading.Lock()


def _ocr():
    global _engine
    with _lock:
        if _engine is None:
            from rapidocr_onnxruntime import RapidOCR

            _engine = RapidOCR()
        return _engine


def extract_image(path: Path) -> list[Block]:
    """Local OCR only: no key, no network. A picture with no readable text
    returns no blocks and stays ready, so a vision caption can describe it later."""
    try:
        pymupdf.Pixmap(str(path))  # validates the bytes really are an image
    except Exception as exc:
        raise ExtractionError("Could not read this file as an image.") from exc
    result, _ = _ocr()(str(path))
    lines = [item[1].strip() for item in (result or []) if item[1].strip()]
    if not lines:
        return []
    return [{"text": "\n".join(lines), "position": {}}]


register("image", (".png", ".jpg", ".jpeg"), extract_image)
