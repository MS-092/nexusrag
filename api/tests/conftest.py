from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from nexusrag.config import Settings
from nexusrag.main import create_app
from tests.fake_provider import FakeProvider


@pytest.fixture(scope="session", autouse=True)
def _warm_embedder():
    """Load the local models once so first-run downloads never race a job."""
    from nexusrag.embedder import get_embedder

    get_embedder().embed_documents(["warm up"])


@pytest.fixture
def data_dir(tmp_path):
    return tmp_path / "data"


@pytest.fixture
def settings(data_dir):
    return Settings(data_dir=data_dir, web_origin="http://localhost:3000")


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app, base_url="http://localhost") as c:
        yield c


@pytest.fixture
def fake_provider():
    provider = FakeProvider().start()
    yield provider
    provider.stop()
