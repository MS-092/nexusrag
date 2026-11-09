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
