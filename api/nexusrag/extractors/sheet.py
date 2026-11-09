from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

from nexusrag.extractors import Block, ExtractionError, register

MAX_ROWS_PER_BLOCK = 50
MAX_ROW_CHARS_PER_BLOCK = 1000  # keeps every block inside one embeddable chunk


def _cell(value: object) -> str:
    return "" if value is None else str(value).strip()


def _read_csv(path: Path) -> Iterator[tuple[str, list[list[str]]]]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    rows = [[_cell(c) for c in row] for row in csv.reader(text.splitlines())]
    yield "CSV", rows


def _read_xlsx(path: Path) -> Iterator[tuple[str, list[list[str]]]]:
    import openpyxl

    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:
        raise ExtractionError("Could not read this file as an Excel workbook.") from exc
    try:
        for ws in wb.worksheets:
            yield ws.title, [[_cell(c) for c in row] for row in ws.iter_rows(values_only=True)]
    finally:
        wb.close()


def _blocks_for_sheet(name: str, rows: list[list[str]]) -> list[Block]:
    numbered = [(i, r) for i, r in enumerate(rows, start=1) if any(r)]
    if len(numbered) < 2:
        return []
    _, header_cells = numbered[0]
    header = [h or f"Column {n}" for n, h in enumerate(header_cells, start=1)]
    prefix = f"Sheet: {name}\nColumns: {' | '.join(header)}\n"

    blocks: list[Block] = []
    lines: list[str] = []
    first = last = 0
    chars = 0

    def flush() -> None:
        nonlocal lines, chars
        if lines:
            blocks.append({"text": prefix + "\n".join(lines), "position": {"sheet": name, "rows": [first, last]}})
        lines, chars = [], 0

    for row_no, cells in numbered[1:]:
        pairs = [f"{header[i] if i < len(header) else f'Column {i + 1}'}: {v}" for i, v in enumerate(cells) if v]
        line = " | ".join(pairs)
        if lines and (len(lines) >= MAX_ROWS_PER_BLOCK or chars + len(line) > MAX_ROW_CHARS_PER_BLOCK):
            flush()
        if not lines:
            first = row_no
        lines.append(line)
        last = row_no
        chars += len(line) + 1
    flush()
    return blocks


def extract_csv(path: Path) -> list[Block]:
    return _finish(_read_csv(path))


def extract_xlsx(path: Path) -> list[Block]:
    return _finish(_read_xlsx(path))


def _finish(sheets: Iterator[tuple[str, list[list[str]]]]) -> list[Block]:
    blocks: list[Block] = []
    for name, rows in sheets:
        blocks.extend(_blocks_for_sheet(name, rows))
    if not blocks:
        raise ExtractionError("No data rows found in this spreadsheet.")
    return blocks


register("spreadsheet", (".csv", ".xlsx"), lambda p: extract_csv(p) if p.suffix == ".csv" else extract_xlsx(p))
