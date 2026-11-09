import httpx


def test_fake_provider_records_openai_compatible_requests(fake_provider):
    res = httpx.post(
        f"{fake_provider.base_url}/v1/chat/completions",
        headers={"Authorization": "Bearer sk-test-123"},
        json={"model": "m", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert res.json()["choices"][0]["message"]["content"] == "fake reply"
    assert len(fake_provider.requests) == 1
    assert fake_provider.requests[0].headers["authorization"] == "Bearer sk-test-123"
    assert "hi" in fake_provider.all_text()


def test_fake_provider_speaks_anthropic_shape(fake_provider):
    res = httpx.post(
        f"{fake_provider.base_url}/v1/messages",
        headers={"x-api-key": "sk-ant-test"},
        json={"model": "m", "messages": []},
    )
    assert res.json()["content"][0]["text"] == "fake reply"
