from tests.helpers import make_pdf, upload, wait_ready

TEXT = (
    "Invoice review\n"
    "The billing team reviewed every invoice this week.\n"
    "Each invoice was matched against the billing ledger and the invoice total was confirmed.\n"
    "Billing owners signed off after the review."
)


def test_tags_are_derived_from_the_text_and_shown_on_the_source(client, app):
    sid = upload(client, "billing.pdf", make_pdf([TEXT])).json()["id"]
    done = wait_ready(client, app, sid)
    assert "invoice" in done["tags"]
    assert "billing" in done["tags"]
    listed = client.get("/sources").json()[0]
    assert listed["tags"] == done["tags"]


def test_common_words_and_numbers_are_never_tags(client, app):
    sid = upload(client, "billing.pdf", make_pdf([TEXT + "\n2026 2026 2026"])).json()["id"]
    done = wait_ready(client, app, sid)
    for noise in ("the", "this", "was", "after", "every", "2026"):
        assert noise not in done["tags"]


def test_tags_are_limited_and_deterministic(client, app):
    data = make_pdf([TEXT])
    a = wait_ready(client, app, upload(client, "a.pdf", data).json()["id"])
    b = wait_ready(client, app, upload(client, "b.pdf", data).json()["id"])
    assert a["tags"] == b["tags"]
    assert 1 <= len(a["tags"]) <= 5


def test_deriving_tags_never_calls_a_provider(client, app, fake_provider):
    upload(client, "billing.pdf", make_pdf([TEXT]))
    app.state.jobs.join()
    assert fake_provider.requests == []
