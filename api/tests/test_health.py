def test_health_reports_component_status(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert set(body) >= {"status", "embedder", "index", "storage"}
    assert body["storage"]["status"] == "ok"


def test_health_creates_data_directory(client, data_dir):
    client.get("/health")
    assert data_dir.is_dir()


def test_cors_allows_only_local_web_origin(client):
    ok = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    bad = client.get("/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in bad.headers


def test_rejects_foreign_host_header(client):
    # DNS rebinding: attacker hostname resolving to 127.0.0.1 must not reach the API.
    assert client.get("/health", headers={"Host": "evil.example"}).status_code == 400
    assert client.get("/health", headers={"Host": "127.0.0.1:8000"}).status_code == 200


def test_cors_is_never_wildcard(client):
    res = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert res.headers.get("access-control-allow-origin") != "*"


def test_health_reflects_embedder_and_index_after_an_ingest(client, app):
    from tests.helpers import make_pdf, upload

    before = client.get("/health").json()
    assert before["index"]["status"] == "ok"
    upload(client, "a.pdf", make_pdf(["Hello health check"]))
    app.state.jobs.join()
    after = client.get("/health").json()
    assert after["embedder"]["status"] == "ready"
    assert after["status"] == "ok"
