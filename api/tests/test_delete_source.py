from tests.helpers import make_pdf, upload, wait_ready

PAGES = ["Quarterly report\nRevenue in Q3 was 4.2 million dollars."]


def ready_source(client, app, name="a.pdf", pages=PAGES):
    sid = upload(client, name, make_pdf(pages)).json()["id"]
    wait_ready(client, app, sid)
    return sid


def test_deleting_a_source_removes_it_from_list_detail_and_retrieval(client, app):
    sid = ready_source(client, app)
    assert client.post("/chat", json={"question": "What was revenue in Q3?"}).json()["citations"]

    res = client.delete(f"/sources/{sid}")
    assert res.status_code == 204
    assert client.get("/sources").json() == []
    assert client.get(f"/sources/{sid}").status_code == 404
    after = client.post("/chat", json={"question": "What was revenue in Q3?"}).json()
    assert after["citations"] == []
    assert after["mode"] == "no_results"


def test_deleting_removes_the_stored_file(client, app, data_dir):
    sid = ready_source(client, app)
    assert (data_dir / "files" / sid).exists()
    client.delete(f"/sources/{sid}")
    assert not (data_dir / "files" / sid).exists()


def test_deleting_an_unknown_source_is_404(client):
    assert client.delete("/sources/nope").status_code == 404


def test_deleted_content_does_not_linger_in_the_extraction_cache(client, app):
    data = make_pdf(PAGES)
    first = upload(client, "a.pdf", data).json()["id"]
    wait_ready(client, app, first)
    client.delete(f"/sources/{first}")
    again = upload(client, "b.pdf", data).json()["id"]
    done = wait_ready(client, app, again)
    assert done["state"] == "ready"
    assert done["cache_hit"] is False        # re-extracted: nothing was retained


def test_cache_is_kept_while_another_source_still_uses_the_same_file(client, app):
    data = make_pdf(PAGES)
    a = upload(client, "a.pdf", data).json()["id"]
    wait_ready(client, app, a)
    b = upload(client, "b.pdf", data).json()["id"]
    wait_ready(client, app, b)
    client.delete(f"/sources/{a}")
    c = upload(client, "c.pdf", data).json()["id"]
    assert wait_ready(client, app, c)["cache_hit"] is True
    # and the surviving copy is still retrievable
    cites = client.post("/chat", json={"question": "What was revenue in Q3?"}).json()["citations"]
    assert {c["source_id"] for c in cites} >= {b}


def test_deleting_other_sources_leaves_the_rest_intact(client, app):
    keep = ready_source(client, app, "keep.pdf", ["Pasta\nBoil the spaghetti for nine minutes in salted water."])
    drop = ready_source(client, app, "drop.pdf")
    client.delete(f"/sources/{drop}")
    ids = [s["id"] for s in client.get("/sources").json()]
    assert ids == [keep]
