from __future__ import annotations

import io

import pymupdf


def make_pdf(pages: list[str]) -> bytes:
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        y = 72
        for line in text.split("\n"):
            page.insert_text((72, y), line, fontsize=11)
            y += 16
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def upload(client, name: str, data: bytes, content_type: str = "application/octet-stream"):
    return client.post("/sources", files={"file": (name, data, content_type)})


def wait_ready(client, app, source_id: str) -> dict:
    app.state.jobs.join()
    res = client.get(f"/sources/{source_id}")
    assert res.status_code == 200
    return res.json()


def make_csv(header: list[str], rows: list[list[object]]) -> bytes:
    import csv

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def make_xlsx(sheets: dict[str, tuple[list[str], list[list[object]]]]) -> bytes:
    import openpyxl

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, (header, rows) in sheets.items():
        ws = wb.create_sheet(name)
        ws.append(header)
        for row in rows:
            ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def make_png(text: str) -> bytes:
    """Render large, clean text into a PNG so OCR has something to read."""
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=200)
    page.insert_text((30, 110), text, fontsize=42)
    return page.get_pixmap(dpi=144).tobytes("png")


def blank_png() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=300, height=200)
    return page.get_pixmap(dpi=96).tobytes("png")
