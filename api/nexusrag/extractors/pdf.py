from __future__ import annotations

from pathlib import Path

import pymupdf

from nexusrag.extractors import Block, ExtractionError, register


def extract_pdf(path: Path) -> list[Block]:
    try:
        doc = pymupdf.open(path)
    except Exception as exc:
        raise ExtractionError("Could not open this file as a PDF.") from exc
    blocks: list[Block] = []
    try:
        for index, page in enumerate(doc, start=1):
            text = page.get_text().strip()
            if text:
                blocks.append({"text": text, "position": {"page": index}})
    finally:
        doc.close()
    if not blocks:
        raise ExtractionError("No extractable text in this PDF (scanned PDFs need OCR).")
    return blocks


register("pdf", (".pdf",), extract_pdf)
