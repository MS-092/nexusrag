from tests.helpers import make_pdf, upload, wait_ready

KEY = "sk-live-SECRET-0123456789abcdef"
BILLING = "Invoice review\nThe billing team reviewed every invoice. Invoice totals were confirmed by finance."
COOKING = "Pasta\nBoil the spaghetti for nine minutes in salted water. Spaghetti needs salt."


def src(client, app, name, text, private=False):
    res = client.post(f"/sources{'?private=true' if private else ''}", files={"file": (name, make_pdf([text]), "application/pdf")})
    sid = res.json()["id"]
    wait_ready(client, app, sid)
    return sid


def notebook(client, name, rules):
    return client.post("/notebooks", json={"name": name, "rules": rules}).json()["id"]


def chat(client, question, scope=None, headers=None):
    body = {"question": question}
    if scope is not None:
        body["scope"] = scope
    return client.post("/chat", json=body, headers=headers or {})


def cited(res):
    return {c["source_id"] for c in res.json()["citations"]}


def test_a_notebook_scope_only_retrieves_from_its_members(client, app):
    billing = src(client, app, "billing.pdf", BILLING)
    cooking = src(client, app, "cooking.pdf", COOKING)
    fin = notebook(client, "Finance", [{"type": "keyword", "value": "invoice"}])

    scoped = chat(client, "What does the document say about salt and spaghetti?", {"type": "notebook", "id": fin})
    assert cooking not in cited(scoped)                 # outside the Notebook, never retrieved

    whole = chat(client, "How long to boil the spaghetti?")
    assert cooking in cited(whole)                      # the Brain scope still sees it

    inside = chat(client, "What did the billing team review?", {"type": "notebook", "id": fin})
    assert cited(inside) == {billing}


def test_the_brain_scope_can_be_stated_explicitly(client, app):
    cooking = src(client, app, "cooking.pdf", COOKING)
    res = chat(client, "How long to boil the spaghetti?", {"type": "brain"})
    assert cooking in cited(res)


def test_private_sources_are_never_in_scope_even_when_pinned_into_a_notebook(client, app, fake_provider):
    secret = src(client, app, "diary.pdf", "Diary\nThe safe code is 4471 and the hiding spot is the attic.", private=True)
    nid = notebook(client, "Mine", [])
    client.put(f"/notebooks/{nid}/pins/{secret}", json={"mode": "in"})
    assert secret in {m["id"] for m in client.get(f"/notebooks/{nid}/sources").json()}   # visible to me

    headers = {"X-Provider": "openai-compatible", "X-Provider-Model": "m", "X-Provider-Key": KEY, "X-Provider-Base-Url": fake_provider.base_url}
    res = chat(client, "What is the safe code?", {"type": "notebook", "id": nid}, headers)
    assert res.json()["mode"] == "no_results"
    assert fake_provider.requests == []


def test_an_empty_notebook_has_nothing_to_answer_from(client, app, fake_provider):
    src(client, app, "cooking.pdf", COOKING)
    nid = notebook(client, "Empty", [{"type": "keyword", "value": "nothing-matches-this"}])
    res = chat(client, "How long to boil the spaghetti?", {"type": "notebook", "id": nid})
    assert res.json()["mode"] == "no_results"


def test_pinning_a_source_out_removes_it_from_the_notebook_scope(client, app):
    cooking = src(client, app, "cooking.pdf", COOKING)
    nid = notebook(client, "Kitchen", [{"type": "keyword", "value": "spaghetti"}])
    assert cooking in cited(chat(client, "How long to boil the spaghetti?", {"type": "notebook", "id": nid}))
    client.put(f"/notebooks/{nid}/pins/{cooking}", json={"mode": "out"})
    assert cited(chat(client, "How long to boil the spaghetti?", {"type": "notebook", "id": nid})) == set()


def test_unknown_notebook_and_bad_scopes_are_rejected(client):
    assert chat(client, "hi", {"type": "notebook", "id": "nope"}).status_code == 404
    assert chat(client, "hi", {"type": "galaxy"}).status_code == 422
    assert chat(client, "hi", {"type": "notebook"}).status_code == 422
