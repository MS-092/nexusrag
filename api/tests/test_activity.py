from tests.helpers import make_pdf, upload, wait_ready

BILLING = "Invoice review\nThe billing team reviewed every invoice. Invoice totals were confirmed by finance."
COOKING = "Pasta\nBoil the spaghetti for nine minutes in salted water. Spaghetti needs salt."


def src(client, app, name, text):
    sid = upload(client, name, make_pdf([text])).json()["id"]
    wait_ready(client, app, sid)
    return sid


def events(client, **params):
    res = client.get("/activity", params=params)
    assert res.status_code == 200, res.text
    return res.json()


def kinds(client, **params):
    return [(e["kind"], e["source_name"]) for e in events(client, **params)]


def test_adding_a_source_is_recorded_once_it_is_ready(client, app):
    sid = src(client, app, "billing.pdf", BILLING)
    got = events(client)
    assert [(e["kind"], e["source_id"], e["source_name"]) for e in got] == [("added", sid, "billing.pdf")]
    assert got[0]["created_at"]


def test_retrying_or_reprocessing_does_not_record_a_second_add(client, app):
    sid = src(client, app, "billing.pdf", BILLING)
    client.post(f"/sources/{sid}/retry")
    app.state.jobs.join()
    assert kinds(client) == [("added", "billing.pdf")]


def test_failed_ingestion_is_not_an_added_source(client, app):
    upload(client, "broken.pdf", b"not a pdf")
    app.state.jobs.join()
    assert events(client) == []


def test_editing_a_note_is_recorded(client, app):
    nid = client.post("/notes", json={"title": "Plan", "content": "# Plan\nShip beta."}).json()["id"]
    app.state.jobs.join()
    client.put(f"/notes/{nid}", json={"title": "Plan", "content": "# Plan\nShip beta on Friday."})
    app.state.jobs.join()
    assert kinds(client) == [("edited", "Plan"), ("added", "Plan")]     # newest first


def test_removing_a_source_is_recorded_and_keeps_its_name(client, app):
    sid = src(client, app, "billing.pdf", BILLING)
    client.delete(f"/sources/{sid}")
    got = events(client)
    assert got[0]["kind"] == "removed"
    assert got[0]["source_name"] == "billing.pdf"
    assert got[0]["source_id"] == sid


def test_a_notebook_only_sees_activity_for_sources_it_contained(client, app):
    fin = client.post("/notebooks", json={"name": "Finance", "rules": [{"type": "keyword", "value": "invoice"}]}).json()["id"]
    src(client, app, "billing.pdf", BILLING)
    src(client, app, "cooking.pdf", COOKING)
    assert kinds(client, notebook_id=fin) == [("added", "billing.pdf")]
    assert len(events(client)) == 2


def test_removal_is_attributed_to_the_notebooks_the_source_was_in(client, app):
    fin = client.post("/notebooks", json={"name": "Finance", "rules": [{"type": "keyword", "value": "invoice"}]}).json()["id"]
    sid = src(client, app, "billing.pdf", BILLING)
    client.delete(f"/sources/{sid}")
    assert kinds(client, notebook_id=fin) == [("removed", "billing.pdf"), ("added", "billing.pdf")]


def test_pinning_a_source_in_makes_its_later_activity_appear_in_the_notebook(client, app):
    fin = client.post("/notebooks", json={"name": "Finance", "rules": []}).json()["id"]
    sid = src(client, app, "cooking.pdf", COOKING)
    client.put(f"/notebooks/{fin}/pins/{sid}", json={"mode": "in"})
    client.delete(f"/sources/{sid}")
    assert kinds(client, notebook_id=fin) == [("removed", "cooking.pdf")]


def test_limit_and_unknown_notebook(client, app):
    for i in range(3):
        src(client, app, f"f{i}.pdf", f"Document number {i} about something unique{i}")
    assert len(events(client, limit=2)) == 2
    assert client.get("/activity", params={"notebook_id": "nope"}).status_code == 404
    assert client.get("/activity", params={"limit": 0}).status_code == 422
