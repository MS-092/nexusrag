from pathlib import Path

from tests.helpers import make_pdf, wait_ready

KEY = "sk-live-SECRET-0123456789abcdef"
FINANCE = ["Quarterly report\nRevenue in Q3 was 4.2 million dollars.", "Appendix\nHeadcount grew to 118 people."]
COOKING = ["Pasta\nBoil the spaghetti for nine minutes in salted water. Spaghetti needs salt."]


def hdrs(base):
    return {"X-Provider": "openai-compatible", "X-Provider-Model": "m", "X-Provider-Key": KEY, "X-Provider-Base-Url": base}


def src(client, app, name, pages):
    sid = client.post("/sources", files={"file": (name, make_pdf(pages), "application/pdf")}).json()["id"]
    wait_ready(client, app, sid)
    return sid


def chat(client, question, **extra):
    headers = extra.pop("headers", {})
    return client.post("/chat", json={"question": question, **extra}, headers=headers)


def test_every_chat_is_saved_and_listed_with_its_scope(client, app):
    src(client, app, "finance.pdf", FINANCE)
    res = chat(client, "What was revenue in Q3?")
    cid = res.json()["conversation_id"]
    rows = client.get("/conversations").json()
    assert [r["id"] for r in rows] == [cid]
    assert rows[0]["title"] == "What was revenue in Q3?"
    assert rows[0]["scope"] == {"type": "brain", "id": None}
    assert rows[0]["message_count"] == 2


def test_follow_ups_append_and_reopening_keeps_citations_intact(client, app):
    fid = src(client, app, "finance.pdf", FINANCE)
    cid = chat(client, "What was revenue in Q3?").json()["conversation_id"]
    second = chat(client, "How many people work there?", conversation_id=cid).json()
    assert second["conversation_id"] == cid

    conv = client.get(f"/conversations/{cid}").json()
    assert [m["role"] for m in conv["messages"]] == ["user", "assistant", "user", "assistant"]
    assert conv["messages"][0]["content"] == "What was revenue in Q3?"
    cite = conv["messages"][1]["citations"][0]
    assert cite["source_id"] == fid and cite["source_name"] == "finance.pdf"
    assert cite["position"] == {"page": 1}
    assert "4.2 million" in cite["quote"]
    assert cite["removed"] is False
    assert conv["messages"][1]["mode"] == "extractive"


def test_conversations_belong_to_a_scope_and_filter_by_it(client, app):
    src(client, app, "finance.pdf", FINANCE)
    src(client, app, "cooking.pdf", COOKING)
    nid = client.post("/notebooks", json={"name": "Kitchen", "rules": [{"type": "keyword", "value": "spaghetti"}]}).json()["id"]
    brain = chat(client, "What was revenue in Q3?").json()["conversation_id"]
    kitchen = chat(client, "How long to boil spaghetti?", scope={"type": "notebook", "id": nid}).json()["conversation_id"]

    in_kitchen = client.get("/conversations", params={"scope": "notebook", "notebook_id": nid}).json()
    assert [c["id"] for c in in_kitchen] == [kitchen]
    in_brain = client.get("/conversations", params={"scope": "brain"}).json()
    assert [c["id"] for c in in_brain] == [brain]
    assert {c["id"] for c in client.get("/conversations").json()} == {brain, kitchen}


def test_a_follow_up_keeps_the_conversations_scope(client, app):
    src(client, app, "finance.pdf", FINANCE)
    src(client, app, "cooking.pdf", COOKING)
    nid = client.post("/notebooks", json={"name": "Kitchen", "rules": [{"type": "keyword", "value": "spaghetti"}]}).json()["id"]
    cid = chat(client, "How long to boil spaghetti?", scope={"type": "notebook", "id": nid}).json()["conversation_id"]
    later = chat(client, "What was revenue in Q3?", conversation_id=cid).json()      # no scope given
    assert later["mode"] == "no_results"                                              # still inside the Notebook


def test_citations_to_a_deleted_source_show_as_removed_but_keep_their_name(client, app):
    fid = src(client, app, "finance.pdf", FINANCE)
    cid = chat(client, "What was revenue in Q3?").json()["conversation_id"]
    client.delete(f"/sources/{fid}")
    cite = client.get(f"/conversations/{cid}").json()["messages"][1]["citations"][0]
    assert cite["removed"] is True
    assert cite["source_name"] == "finance.pdf"


def test_deleting_a_conversation_and_unknown_ids(client, app):
    src(client, app, "finance.pdf", FINANCE)
    cid = chat(client, "What was revenue in Q3?").json()["conversation_id"]
    assert client.delete(f"/conversations/{cid}").status_code == 204
    assert client.get(f"/conversations/{cid}").status_code == 404
    assert client.delete(f"/conversations/{cid}").status_code == 404
    assert client.get("/conversations").json() == []
    assert chat(client, "hello there", conversation_id="nope").status_code == 404


def test_the_key_is_never_saved_with_a_conversation(client, app, fake_provider, data_dir):
    src(client, app, "finance.pdf", FINANCE)
    fake_provider.reply = "Revenue was 4.2 million [1]."
    res = chat(client, "What was revenue in Q3?", headers=hdrs(fake_provider.base_url))
    cid = res.json()["conversation_id"]
    assert KEY not in client.get(f"/conversations/{cid}").text
    for path in Path(data_dir).rglob("*"):
        if path.is_file():
            assert KEY.encode() not in path.read_bytes(), f"key leaked into {path}"


def test_a_failed_provider_call_saves_nothing(client, app, fake_provider):
    src(client, app, "finance.pdf", FINANCE)
    fake_provider.status = 401
    assert chat(client, "What was revenue in Q3?", headers=hdrs(fake_provider.base_url)).status_code == 401
    assert client.get("/conversations").json() == []


def test_skill_replies_are_saved_with_their_skill(client, app):
    src(client, app, "finance.pdf", FINANCE)
    cid = chat(client, "/summarize").json()["conversation_id"]
    msg = client.get(f"/conversations/{cid}").json()["messages"][1]
    assert msg["skill"] == "summarize"


def test_no_results_answers_are_saved_too(client):
    cid = chat(client, "anything at all?").json()["conversation_id"]
    conv = client.get(f"/conversations/{cid}").json()
    assert conv["messages"][1]["mode"] == "no_results"
    assert conv["messages"][1]["citations"] == []
