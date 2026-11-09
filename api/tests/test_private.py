from tests.helpers import make_pdf, make_png, upload, wait_ready

KEY = "sk-live-SECRET-0123456789abcdef"
SECRET = "Project Zebra budget is 9.9 million"


def hdrs(base):
    return {"X-Provider": "openai-compatible", "X-Provider-Model": "m", "X-Provider-Base-Url": base, "X-Provider-Key": KEY}


def pdf(client, app, name, text, private=False):
    res = client.post(
        f"/sources{'?private=true' if private else ''}",
        files={"file": (name, make_pdf([text]), "application/pdf")},
    )
    assert res.status_code == 202, res.text
    sid = res.json()["id"]
    wait_ready(client, app, sid)
    return sid


def test_marking_a_source_private_removes_it_from_chat_but_not_from_the_list(client, app, fake_provider):
    sid = pdf(client, app, "plan.pdf", SECRET)
    assert client.post("/chat", json={"question": "What is the Project Zebra budget?"}).json()["citations"]

    res = client.patch(f"/sources/{sid}", json={"private": True})
    assert res.status_code == 200
    assert res.json()["private"] is True

    listed = client.get("/sources").json()
    assert [s["id"] for s in listed] == [sid] and listed[0]["private"] is True   # still visible to me
    assert SECRET.split()[0] in client.get(f"/sources/{sid}").json()["extracted_text"]

    body = client.post(
        "/chat", json={"question": "What is the Project Zebra budget?"}, headers=hdrs(fake_provider.base_url)
    ).json()
    assert body["mode"] == "no_results"
    assert fake_provider.requests == []


def test_private_content_never_appears_in_a_provider_request_even_when_other_sources_match(client, app, fake_provider):
    pdf(client, app, "plan.pdf", SECRET, private=True)
    pdf(client, app, "public.pdf", "Project Zebra is a public pilot run by the marketing team.")
    fake_provider.reply = "A public pilot [1]."
    client.post("/chat", json={"question": "Tell me about Project Zebra"}, headers=hdrs(fake_provider.base_url))
    assert fake_provider.requests, "the public source should have been answered with the model"
    assert "9.9 million" not in fake_provider.all_text()


def test_unmarking_makes_a_source_retrievable_again(client, app):
    sid = pdf(client, app, "plan.pdf", SECRET, private=True)
    assert client.post("/chat", json={"question": "Project Zebra budget"}).json()["mode"] == "no_results"
    client.patch(f"/sources/{sid}", json={"private": False})
    assert client.post("/chat", json={"question": "Project Zebra budget"}).json()["citations"]


def test_private_images_are_never_sent_for_captioning(client, app, fake_provider):
    res = client.post(
        "/sources?private=true",
        files={"file": ("shot.png", make_png("Salary 123456"), "image/png")},
        headers=hdrs(fake_provider.base_url),
    )
    sid = res.json()["id"]
    done = wait_ready(client, app, sid)
    assert done["private"] is True
    assert done["captioned"] is False
    assert "123456" in done["extracted_text"]          # local OCR still works
    assert fake_provider.requests == []                # nothing left the machine


def test_a_private_image_cannot_be_captioned_later(client, app, fake_provider):
    res = client.post("/sources?private=true", files={"file": ("shot.png", make_png("Salary 123456"), "image/png")})
    sid = res.json()["id"]
    wait_ready(client, app, sid)
    again = client.post(f"/sources/{sid}/caption", headers=hdrs(fake_provider.base_url))
    assert again.status_code == 400
    assert "private" in again.json()["detail"].lower()
    assert fake_provider.requests == []


def test_a_private_image_is_never_attached_to_a_chat_call(client, app, fake_provider):
    fake_provider.reply = "A bar chart of salaries."
    sid, _ = None, None
    res = client.post(
        "/sources", files={"file": ("shot.png", make_png("Salary 123456"), "image/png")}, headers=hdrs(fake_provider.base_url)
    )
    sid = res.json()["id"]
    wait_ready(client, app, sid)
    client.patch(f"/sources/{sid}", json={"private": True})
    before = len(fake_provider.requests)
    client.post("/chat", json={"question": "What salary is shown?"}, headers=hdrs(fake_provider.base_url))
    assert len(fake_provider.requests) == before        # no model call at all
    assert "data:image" not in "".join(r.raw for r in fake_provider.requests[before:])


def test_private_notes(client, app, fake_provider):
    res = client.post("/notes", json={"title": "Diary", "content": "# Diary\nThe safe code is 4471.", "private": True})
    assert res.status_code == 202
    assert res.json()["private"] is True
    app.state.jobs.join()
    body = client.post("/chat", json={"question": "What is the safe code?"}, headers=hdrs(fake_provider.base_url)).json()
    assert body["mode"] == "no_results"
    assert fake_provider.requests == []


def test_patching_an_unknown_source_is_404_and_a_bad_body_is_rejected(client, app):
    assert client.patch("/sources/nope", json={"private": True}).status_code == 404
    sid = pdf(client, app, "a.pdf", "Hello there friend")
    assert client.patch(f"/sources/{sid}", json={}).status_code == 422
