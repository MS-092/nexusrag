from tests.helpers import make_pdf, upload, wait_ready


def create_note(client, app, title="Launch plan", content="# Launch plan\nThe beta ships on Friday with the purple theme."):
    res = client.post("/notes", json={"title": title, "content": content})
    assert res.status_code == 202, res.text
    sid = res.json()["id"]
    app.state.jobs.join()
    return sid


def test_creating_a_note_returns_processing_then_becomes_ready(client, app):
    res = client.post("/notes", json={"title": "Launch plan", "content": "# Plan\nBeta ships on Friday."})
    assert res.status_code == 202
    body = res.json()
    assert body["state"] == "processing"
    assert body["kind"] == "note"
    assert body["name"] == "Launch plan"
    done = wait_ready(client, app, body["id"])
    assert done["state"] == "ready"
    assert done["chunk_count"] >= 1
    assert "Beta ships on Friday" in done["extracted_text"]


def test_notes_are_citable_in_chat_like_any_source(client, app):
    sid = create_note(client, app)
    body = client.post("/chat", json={"question": "When does the beta ship?"}).json()
    top = body["citations"][0]
    assert top["source_id"] == sid
    assert top["kind"] == "note"
    assert top["source_name"] == "Launch plan"


def test_get_note_returns_the_raw_markdown_for_editing(client, app):
    content = "# Launch plan\n\n- ship **beta**\n- announce"
    sid = create_note(client, app, content=content)
    res = client.get(f"/notes/{sid}")
    assert res.status_code == 200
    assert res.json() == {"id": sid, "title": "Launch plan", "content": content}


def test_editing_a_note_replaces_what_the_brain_knows(client, app):
    sid = create_note(client, app, content="# Plan\nThe codename is Bluebird.")
    assert client.post("/chat", json={"question": "What is the codename?"}).json()["citations"]

    res = client.put(f"/notes/{sid}", json={"title": "Launch plan", "content": "# Plan\nThe codename is Sparrowhawk."})
    assert res.status_code == 202
    assert res.json()["state"] == "processing"
    app.state.jobs.join()

    done = client.get(f"/sources/{sid}").json()
    assert "Sparrowhawk" in done["extracted_text"]
    assert "Bluebird" not in done["extracted_text"]
    cites = client.post("/chat", json={"question": "What is the codename?"}).json()["citations"]
    assert all("Bluebird" not in c["quote"] for c in cites)
    assert any("Sparrowhawk" in c["quote"] for c in cites)


def test_edit_can_rename_the_note(client, app):
    sid = create_note(client, app)
    client.put(f"/notes/{sid}", json={"title": "Release plan", "content": "# Plan\nBeta ships Friday."})
    app.state.jobs.join()
    assert client.get(f"/sources/{sid}").json()["name"] == "Release plan"


def test_old_note_text_does_not_linger_in_the_cache_after_an_edit(client, app):
    sid = create_note(client, app, content="# Plan\nThe codename is Bluebird.")
    client.put(f"/notes/{sid}", json={"title": "Launch plan", "content": "# Plan\nThe codename is Sparrowhawk."})
    app.state.jobs.join()
    again = create_note(client, app, title="Copy", content="# Plan\nThe codename is Bluebird.")
    assert client.get(f"/sources/{again}").json()["cache_hit"] is False


def test_blank_title_or_content_is_rejected(client):
    assert client.post("/notes", json={"title": "  ", "content": "x"}).status_code in (400, 422)
    assert client.post("/notes", json={"title": "t", "content": "   "}).status_code in (400, 422)


def test_editing_an_unknown_note_is_404(client):
    assert client.put("/notes/nope", json={"title": "t", "content": "x"}).status_code == 404
    assert client.get("/notes/nope").status_code == 404


def test_only_notes_can_be_edited_as_notes(client, app):
    pdf = upload(client, "a.pdf", make_pdf(["Hello there friend"])).json()["id"]
    app.state.jobs.join()
    assert client.put(f"/notes/{pdf}", json={"title": "t", "content": "x"}).status_code == 400
    assert client.get(f"/notes/{pdf}").status_code == 400


def test_markdown_files_cannot_be_uploaded_notes_are_written_in_the_app(client):
    res = upload(client, "notes.md", b"# hello")
    assert res.status_code == 415
