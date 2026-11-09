from tests.helpers import make_pdf, wait_ready

KEY = "sk-live-SECRET-0123456789abcdef"
BILLING = ["Invoice review\nThe billing team reviewed every invoice. Invoice totals were confirmed by finance."]
COOKING = ["Pasta\nBoil the spaghetti for nine minutes in salted water. Spaghetti needs salt."]
PRIVATE = ["Diary\nThe safe code is 4471 and the hiding spot is the attic."]


def hdrs(base):
    return {"X-Provider": "openai-compatible", "X-Provider-Model": "m", "X-Provider-Key": KEY, "X-Provider-Base-Url": base}


def src(client, app, name, pages, private=False):
    res = client.post(f"/sources{'?private=true' if private else ''}", files={"file": (name, make_pdf(pages), "application/pdf")})
    sid = res.json()["id"]
    wait_ready(client, app, sid)
    return sid


def nb(client, name, rules):
    return client.post("/notebooks", json={"name": name, "rules": rules}).json()["id"]


def status(client, scope=None, headers=None, text="/status"):
    body = {"question": text}
    if scope:
        body["scope"] = scope
    res = client.post("/chat", json=body, headers=headers or {})
    assert res.status_code == 200, res.text
    return res.json()


def test_status_is_listed_as_a_shipped_skill(client):
    assert "status" in {s["name"] for s in client.get("/skills").json()}


def test_status_shows_every_notebook_with_contents_summary_and_recent_activity(client, app):
    fin = nb(client, "Finance", [{"type": "keyword", "value": "invoice"}])
    kit = nb(client, "Kitchen", [{"type": "keyword", "value": "spaghetti"}])
    src(client, app, "billing.pdf", BILLING)
    src(client, app, "cooking.pdf", COOKING)

    body = status(client)
    assert body["skill"] == "status"
    by_name = {n["name"]: n for n in body["status"]["notebooks"]}
    assert set(by_name) == {"Finance", "Kitchen"}

    finance = by_name["Finance"]
    assert finance["id"] == fin
    assert finance["member_count"] == 1
    assert finance["sources"] == [{"name": "billing.pdf", "private": False}]
    assert finance["summary"]
    assert [a["kind"] for a in finance["activity"]] == ["added"]
    assert finance["activity"][0]["source_name"] == "billing.pdf"
    assert by_name["Kitchen"]["sources"][0]["name"] == "cooking.pdf"

    assert body["status"]["brain"]["sources"] == 2
    assert [a["source_name"] for a in body["status"]["activity"]] == ["cooking.pdf", "billing.pdf"]
    assert "Finance" in body["answer"] and "Kitchen" in body["answer"]


def test_status_always_covers_the_whole_brain_whatever_the_scope(client, app):
    fin = nb(client, "Finance", [{"type": "keyword", "value": "invoice"}])
    nb(client, "Kitchen", [{"type": "keyword", "value": "spaghetti"}])
    src(client, app, "billing.pdf", BILLING)
    src(client, app, "cooking.pdf", COOKING)
    body = status(client, scope={"type": "notebook", "id": fin})
    assert {n["name"] for n in body["status"]["notebooks"]} == {"Finance", "Kitchen"}
    assert body["status"]["brain"]["sources"] == 2


def test_status_ignores_any_argument(client, app):
    nb(client, "Finance", [{"type": "keyword", "value": "invoice"}])
    src(client, app, "billing.pdf", BILLING)
    assert status(client, text="/status please ignore this")["status"]["brain"]["sources"] == 1


def test_offline_summary_names_the_notebook_topics(client, app, fake_provider):
    nb(client, "Finance", [{"type": "keyword", "value": "invoice"}])
    src(client, app, "billing.pdf", BILLING)
    body = status(client)
    assert body["mode"] == "extractive"
    summary = body["status"]["notebooks"][0]["summary"].lower()
    assert "invoice" in summary or "billing" in summary
    assert fake_provider.requests == []


def test_with_a_provider_each_notebook_gets_a_model_written_summary(client, app, fake_provider):
    nb(client, "Finance", [{"type": "keyword", "value": "invoice"}])
    src(client, app, "billing.pdf", BILLING)
    fake_provider.reply = "Invoice reviews handled by the billing team."
    body = status(client, headers=hdrs(fake_provider.base_url))
    assert body["mode"] == "model"
    assert body["status"]["notebooks"][0]["summary"] == "Invoice reviews handled by the billing team."
    assert "Invoice totals were confirmed" in fake_provider.requests[0].raw


def test_private_content_is_listed_for_me_but_never_sent_to_a_provider(client, app, fake_provider):
    nb(client, "Everything", [{"type": "keyword", "value": "the"}])
    src(client, app, "billing.pdf", BILLING)
    src(client, app, "diary.pdf", PRIVATE, private=True)
    fake_provider.reply = "A mix of material."
    body = status(client, headers=hdrs(fake_provider.base_url))
    listed = {s["name"]: s["private"] for s in body["status"]["notebooks"][0]["sources"]}
    assert listed == {"billing.pdf": False, "diary.pdf": True}          # I can see it locally
    assert "4471" not in fake_provider.all_text()                         # the provider cannot
    assert "diary.pdf" not in fake_provider.all_text()


def test_a_notebook_with_only_private_sources_gets_no_model_call(client, app, fake_provider):
    nb(client, "Secrets", [{"type": "keyword", "value": "safe"}])
    src(client, app, "diary.pdf", PRIVATE, private=True)
    body = status(client, headers=hdrs(fake_provider.base_url))
    assert fake_provider.requests == []
    assert body["status"]["notebooks"][0]["member_count"] == 1


def test_recent_activity_is_limited_to_the_last_five(client, app):
    nb(client, "All", [{"type": "keyword", "value": "document"}])
    for i in range(7):
        src(client, app, f"f{i}.pdf", [f"Document number {i} with something unique{i}"])
    body = status(client)
    assert len(body["status"]["activity"]) == 5
    assert len(body["status"]["notebooks"][0]["activity"]) == 5
    assert body["status"]["activity"][0]["source_name"] == "f6.pdf"


def test_an_empty_brain_says_so(client):
    body = status(client)
    assert body["status"]["brain"]["sources"] == 0
    assert body["status"]["notebooks"] == []
    assert "empty" in body["answer"].lower()


def test_a_provider_error_in_status_is_reported_clearly(client, app, fake_provider):
    nb(client, "Finance", [{"type": "keyword", "value": "invoice"}])
    src(client, app, "billing.pdf", BILLING)
    fake_provider.status = 401
    res = client.post("/chat", json={"question": "/status"}, headers=hdrs(fake_provider.base_url))
    assert res.status_code == 401
    assert KEY not in res.text
