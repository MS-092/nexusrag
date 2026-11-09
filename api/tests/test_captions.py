from pathlib import Path

from tests.helpers import make_pdf, make_png, upload, wait_ready

KEY = "sk-live-SECRET-0123456789abcdef"


def hdrs(base, provider="openai-compatible", key=KEY):
    h = {"X-Provider": provider, "X-Provider-Model": "vision-test", "X-Provider-Base-Url": base}
    if key:
        h["X-Provider-Key"] = key
    return h


def up_image(client, app, name="chart.png", text="Revenue 4200", headers=None):
    res = client.post("/sources", files={"file": (name, make_png(text), "image/png")}, headers=headers or {})
    assert res.status_code == 202, res.text
    sid = res.json()["id"]
    return sid, wait_ready(client, app, sid)


def test_image_uploaded_with_a_key_gets_a_vision_caption(client, app, fake_provider):
    fake_provider.reply = "A bar chart of quarterly revenue, Q3 is the tallest bar at 4.2 million."
    sid, done = up_image(client, app, headers=hdrs(fake_provider.base_url))
    assert done["state"] == "ready"
    assert done["captioned"] is True
    assert "tallest bar" in done["extracted_text"]
    assert "4200" in done["extracted_text"]                     # OCR text is kept too

    sent = fake_provider.requests[0]
    assert sent.headers["authorization"] == f"Bearer {KEY}"
    assert "data:image/png;base64," in sent.raw                 # the image went to the provider


def test_anthropic_caption_uses_its_image_block_format(client, app, fake_provider):
    fake_provider.reply = "A line chart."
    sid, done = up_image(client, app, headers=hdrs(fake_provider.base_url, "anthropic"))
    assert done["captioned"] is True
    body = fake_provider.requests[0].body
    block = body["messages"][0]["content"][0]
    assert block["type"] == "image"
    assert block["source"]["type"] == "base64"
    assert block["source"]["media_type"] == "image/png"


def test_image_uploaded_without_a_key_is_indexed_from_ocr_only(client, app, fake_provider):
    sid, done = up_image(client, app)
    assert done["state"] == "ready"
    assert done["captioned"] is False
    assert "4200" in done["extracted_text"]
    assert fake_provider.requests == []


def test_an_image_can_be_captioned_later_by_a_request_that_carries_a_key(client, app, fake_provider):
    sid, before = up_image(client, app)
    assert before["captioned"] is False
    fake_provider.reply = "A bar chart showing revenue."
    res = client.post(f"/sources/{sid}/caption", headers=hdrs(fake_provider.base_url))
    assert res.status_code == 202
    assert res.json()["state"] == "processing"
    app.state.jobs.join()
    after = client.get(f"/sources/{sid}").json()
    assert after["captioned"] is True
    assert "bar chart" in after["extracted_text"]
    assert len(fake_provider.requests) == 1


def test_captioning_needs_a_provider(client, app):
    sid, _ = up_image(client, app)
    res = client.post(f"/sources/{sid}/caption")
    assert res.status_code == 400
    assert "provider" in res.json()["detail"].lower()


def test_only_images_can_be_captioned(client, app, fake_provider):
    pdf = upload(client, "a.pdf", make_pdf(["Hello there friend"])).json()["id"]
    app.state.jobs.join()
    res = client.post(f"/sources/{pdf}/caption", headers=hdrs(fake_provider.base_url))
    assert res.status_code == 400


def test_the_same_image_is_never_captioned_twice(client, app, fake_provider):
    fake_provider.reply = "A bar chart."
    up_image(client, app, name="a.png", headers=hdrs(fake_provider.base_url))
    assert len(fake_provider.requests) == 1
    _, second = up_image(client, app, name="b.png", headers=hdrs(fake_provider.base_url))
    assert second["captioned"] is True
    assert second["cache_hit"] is True
    assert len(fake_provider.requests) == 1                     # served from the cache


def test_a_failing_provider_does_not_fail_ingestion_and_never_echoes_the_key(client, app, fake_provider):
    fake_provider.status = 401
    sid, done = up_image(client, app, headers=hdrs(fake_provider.base_url))
    assert done["state"] == "ready"
    assert done["captioned"] is False
    assert "4200" in done["extracted_text"]
    assert "rejected" in done["error"].lower()
    assert KEY not in str(done)


def test_top_image_hits_are_attached_to_the_chat_model_call(client, app, fake_provider):
    fake_provider.reply = "A bar chart showing quarterly revenue of 4.2 million."
    up_image(client, app, headers=hdrs(fake_provider.base_url))
    fake_provider.reply = "The chart shows revenue [1]."
    res = client.post(
        "/chat", json={"question": "What does the revenue chart show?"}, headers=hdrs(fake_provider.base_url)
    )
    assert res.json()["mode"] == "model"
    chat_call = fake_provider.requests[-1]
    assert "data:image/png;base64," in chat_call.raw


def test_the_key_is_never_written_to_disk_by_captioning(client, app, fake_provider, data_dir):
    up_image(client, app, headers=hdrs(fake_provider.base_url))
    for path in Path(data_dir).rglob("*"):
        if path.is_file():
            assert KEY.encode() not in path.read_bytes(), f"key leaked into {path}"
