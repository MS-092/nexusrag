import logging
from pathlib import Path

from tests.helpers import make_csv, make_pdf, upload, wait_ready

KEY = "sk-live-SECRET-0123456789abcdef"

DOCS = {
    "finance.pdf": ["Quarterly report\nRevenue in Q3 was 4.2 million dollars.", "Appendix\nHeadcount grew to 118 people."],
    "ops.pdf": ["Runbook\nInvoice INV-8841 was escalated to the billing team on Tuesday."],
    "cooking.pdf": ["Pasta\nBoil the spaghetti for nine minutes in salted water."],
}


def seed(client, app, docs=DOCS):
    ids = {}
    for name, pages in docs.items():
        ids[name] = upload(client, name, make_pdf(pages)).json()["id"]
    app.state.jobs.join()
    return ids


def headers(provider="openai-compatible", base=None, model="test-model", key=KEY):
    h = {"X-Provider": provider, "X-Provider-Model": model}
    if base:
        h["X-Provider-Base-Url"] = base
    if key is not None:
        h["X-Provider-Key"] = key
    return h


def ask(client, question, **kw):
    return client.post("/chat", json={"question": question}, headers=kw.get("headers", {}))


def test_without_a_key_chat_gives_an_extractive_answer_with_citations(client, app, fake_provider):
    ids = seed(client, app)
    res = ask(client, "What was revenue in Q3?")
    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "extractive"
    assert "4.2 million" in body["answer"]
    top = body["citations"][0]
    assert top["source_id"] == ids["finance.pdf"]
    assert top["source_name"] == "finance.pdf"
    assert top["position"] == {"page": 1}
    assert "4.2 million" in top["quote"]
    assert top["n"] == 1
    assert fake_provider.requests == []


def test_with_a_key_the_provider_answers_from_retrieved_passages(client, app, fake_provider):
    seed(client, app)
    fake_provider.reply = "Revenue in Q3 was 4.2 million dollars [1]."
    res = ask(client, "What was revenue in Q3?", headers=headers(base=fake_provider.base_url))
    body = res.json()
    assert res.status_code == 200
    assert body["mode"] == "model"
    assert body["answer"] == "Revenue in Q3 was 4.2 million dollars [1]."
    assert body["citations"]

    sent = fake_provider.requests[0]
    assert sent.headers["authorization"] == f"Bearer {KEY}"      # key travelled per request
    assert sent.body["model"] == "test-model"
    assert "4.2 million" in sent.raw                             # grounded in the passage
    assert "What was revenue in Q3?" in sent.raw


def test_anthropic_provider_uses_its_own_wire_format(client, app, fake_provider):
    seed(client, app)
    fake_provider.reply = "From the report [1]."
    res = ask(client, "What was revenue in Q3?", headers=headers("anthropic", fake_provider.base_url, "claude-test"))
    assert res.json()["answer"] == "From the report [1]."
    sent = fake_provider.requests[0]
    assert sent.path.endswith("/v1/messages")
    assert sent.headers["x-api-key"] == KEY
    assert "system" in sent.body


def test_exact_terms_are_found_even_when_meaning_search_would_miss_them(client, app):
    ids = seed(client, app)
    body = ask(client, "INV-8841").json()
    assert body["citations"][0]["source_id"] == ids["ops.pdf"]


def test_spreadsheet_citations_carry_sheet_and_row_range(client, app):
    rows = [[f"Region{i}", 1000 + i] for i in range(120)]
    sid = upload(client, "sales.csv", make_csv(["Region", "Revenue"], rows)).json()["id"]
    wait_ready(client, app, sid)
    body = ask(client, "Region77 revenue").json()
    pos = body["citations"][0]["position"]
    assert body["citations"][0]["source_id"] == sid
    assert pos["sheet"] == "CSV"
    first, last = pos["rows"]
    assert first <= 78 <= last          # data row for Region77 (header is row 1)


def test_empty_brain_says_there_is_nothing_to_answer_from(client, fake_provider):
    res = ask(client, "anything at all?", headers=headers(base=fake_provider.base_url))
    body = res.json()
    assert body["mode"] == "no_results"
    assert body["citations"] == []
    assert "not enough information" in body["answer"].lower()
    assert fake_provider.requests == []      # never ask a model to guess


def test_unrelated_question_is_refused_not_guessed(client, app, fake_provider):
    seed(client, app, {"finance.pdf": DOCS["finance.pdf"]})
    res = ask(client, "Who won the 1998 football world cup final?", headers=headers(base=fake_provider.base_url))
    assert res.json()["mode"] == "no_results"
    assert fake_provider.requests == []


def test_key_never_appears_in_logs_responses_or_data_files(client, app, fake_provider, caplog, data_dir):
    seed(client, app)
    caplog.set_level(logging.DEBUG)
    res = ask(client, "What was revenue in Q3?", headers=headers(base=fake_provider.base_url))
    assert KEY not in res.text
    assert KEY not in caplog.text
    for path in Path(data_dir).rglob("*"):
        if path.is_file():
            assert KEY.encode() not in path.read_bytes(), f"key leaked into {path}"


def test_wrong_key_gives_a_clear_error_without_echoing_the_key(client, app, fake_provider):
    seed(client, app)
    fake_provider.status = 401
    res = ask(client, "What was revenue in Q3?", headers=headers(base=fake_provider.base_url))
    assert res.status_code == 401
    assert "key" in res.json()["detail"].lower()
    assert KEY not in res.text


def test_unreachable_provider_gives_a_clear_error(client, app):
    seed(client, app)
    res = ask(client, "What was revenue in Q3?", headers=headers(base="http://127.0.0.1:1"))
    assert res.status_code == 502
    assert "reach" in res.json()["detail"].lower()
    assert KEY not in res.text


def test_anthropic_requires_a_key(client, app):
    seed(client, app)
    res = ask(client, "What was revenue in Q3?", headers=headers("anthropic", key=None))
    assert res.status_code == 400
    assert "key" in res.json()["detail"].lower()


def test_unknown_provider_is_rejected(client, app):
    res = ask(client, "hi", headers={"X-Provider": "skynet", "X-Provider-Key": KEY})
    assert res.status_code == 400
    assert KEY not in res.text


def test_blank_question_is_rejected(client):
    res = client.post("/chat", json={"question": "   "})
    assert res.status_code == 422 or res.status_code == 400
