from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.config import settings
from app.main import app


@pytest.fixture()
def doc_path(tmp_path):
    """Temporary file path used as document_path during tests"""
    return tmp_path / "document.txt"


@pytest.fixture()
def client(doc_path, monkeypatch):
    monkeypatch.setattr(settings, "DOCUMENT_DIR", doc_path.parent)
    return TestClient(app)

class TestUploadDocument:

    def test_returns_201_on_success(self, client):
        r = client.post(
            "/documents",
            content="Hello world",
            headers={"Content-Type": "text/plain"},
        )
        assert r.status_code == 201

    def test_response_contains_status_and_character_count(self, client):
        r = client.post(
            "/documents",
            content="Hello world",
            headers={"Content-Type": "text/plain"},
        )
        body = r.json()
        assert body["status"] == "success"
        assert body["characters"] == 11

    def test_text_is_written_to_disk(self, client, doc_path):
        text = "Some random text to upload"
        client.post(
            "/documents",
            content=text,
            headers={"Content-Type": "text/plain"},
        )
        assert doc_path.read_text(encoding="utf-8") == text


    def test_empty_body_returns_400(self, client):
        r = client.post(
            "/documents",
            content="",
            headers={"Content-Type": "text/plain"},
        )
        assert r.status_code == 422

    def test_oversized_body_returns_422(self, client):
        r = client.post(
            "/documents",
            content="abc" * settings.MAX_DOCUMENT_CHARS,
            headers={"Content-Type": "text/plain"},
        )
        assert r.status_code == 422

    def test_max_allowed_size_accepted(self, client):
        r = client.post(
            "/documents",
            content="a" * settings.MAX_DOCUMENT_CHARS,
            headers={"Content-Type": "text/plain"},
        )
        assert r.status_code == 201