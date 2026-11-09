from tests.helpers import make_pdf, upload, wait_ready

REPORT = ["Quarterly report\nRevenue in Q3 was 4.2 million dollars.", "Appendix\nHeadcount grew to 118 people."]


def test_upload_returns_processing_immediately_then_becomes_ready(client, app):
    res = upload(client, "report.pdf", make_pdf(REPORT))
    assert res.status_code in (200, 201, 202)
    body = res.json()
    assert body["state"] == "processing"
    assert body["kind"] == "pdf"
    assert body["name"] == "report.pdf"

    done = wait_ready(client, app, body["id"])
    assert done["state"] == "ready"
    assert done["chunk_count"] >= 2          # one page each at minimum
    assert "Revenue in Q3 was 4.2 million" in done["extracted_text"]
    assert "Headcount grew to 118" in done["extracted_text"]


def test_sources_list_shows_state_and_omits_full_text(client, app):
    sid = upload(client, "report.pdf", make_pdf(REPORT)).json()["id"]
    wait_ready(client, app, sid)
    rows = client.get("/sources").json()
    assert [r["id"] for r in rows] == [sid]
    assert rows[0]["state"] == "ready"
    assert "extracted_text" not in rows[0]


def test_reuploading_identical_file_is_served_from_the_cache(client, app):
    data = make_pdf(REPORT)
    first = upload(client, "a.pdf", data).json()
    assert wait_ready(client, app, first["id"])["cache_hit"] is False

    second = upload(client, "b.pdf", data).json()
    done = wait_ready(client, app, second["id"])
    assert done["state"] == "ready"
    assert done["cache_hit"] is True
    assert "Revenue in Q3" in done["extracted_text"]


def test_corrupt_pdf_fails_with_a_message_and_can_be_retried(client, app):
    res = upload(client, "broken.pdf", b"this is not a pdf")
    sid = res.json()["id"]
    done = wait_ready(client, app, sid)
    assert done["state"] == "failed"
    assert done["error"]

    retry = client.post(f"/sources/{sid}/retry")
    assert retry.status_code in (200, 202)
    assert retry.json()["state"] == "processing"
    assert wait_ready(client, app, sid)["state"] == "failed"


def test_pdf_without_text_fails_clearly(client, app):
    sid = upload(client, "blank.pdf", make_pdf([""])).json()["id"]
    done = wait_ready(client, app, sid)
    assert done["state"] == "failed"
    assert "text" in done["error"].lower()


def test_upload_over_the_size_limit_is_rejected(client):
    big = b"x" * (client.app.state.settings.max_upload_bytes + 1)
    res = upload(client, "big.pdf", big)
    assert res.status_code == 413
    assert "50 MB" in res.json()["detail"] or "limit" in res.json()["detail"].lower()


def test_unsupported_file_type_is_rejected_with_the_accepted_list(client):
    res = upload(client, "malware.exe", b"MZ")
    assert res.status_code == 415
    assert ".pdf" in res.json()["detail"]


def test_unknown_source_is_404(client):
    assert client.get("/sources/does-not-exist").status_code == 404
