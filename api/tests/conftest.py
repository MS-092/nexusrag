from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from nexusrag.config import Settings
from nexusrag.main import create_app
from tests.fake_provider import FakeProvider


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
    with TestClient(app) as c:
        yield c


@pytest.fixture
def fake_provider():
    provider = FakeProvider().start()
    yield provider
    provider.stop()
