from tests.helpers import blank_png, make_png, upload, wait_ready


def test_image_text_is_extracted_locally_without_any_key(client, app, fake_provider):
    sid = upload(client, "screenshot.png", make_png("Revenue 4200")).json()["id"]
    done = wait_ready(client, app, sid)
    assert done["state"] == "ready"
    assert done["kind"] == "image"
    assert "4200" in done["extracted_text"]
    assert done["chunk_count"] >= 1
    assert fake_provider.requests == []     # nothing left the machine


def test_jpeg_extension_is_accepted(client, app):
    res = upload(client, "photo.jpg", make_png("Invoice 8841"))
    assert res.status_code == 202
    assert res.json()["kind"] == "image"


def test_image_without_text_is_ready_but_empty_so_it_can_be_captioned_later(client, app):
    sid = upload(client, "chart.png", blank_png()).json()["id"]
    done = wait_ready(client, app, sid)
    assert done["state"] == "ready"
    assert done["chunk_count"] == 0
    assert done["extracted_text"] == ""


def test_corrupt_image_fails_with_a_message(client, app):
    sid = upload(client, "broken.png", b"not an image").json()["id"]
    done = wait_ready(client, app, sid)
    assert done["state"] == "failed"
    assert done["error"]
