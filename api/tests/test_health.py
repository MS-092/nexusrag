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


def test_cors_is_never_wildcard(client):
    res = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert res.headers.get("access-control-allow-origin") != "*"
