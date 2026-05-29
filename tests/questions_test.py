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


@pytest.fixture()
def client_with_doc(client, doc_path):
    """TestClient that already has a document uploaded."""
    client.post(
        "/documents",
        content="Dart platform is used by Barclays front office developers to build and deploy their applications without worrying about the underlying infrastructure." \
        "The platform provides a seamless experience for developers, allowing them to focus on writing code and delivering value to their users. " \
        "With Dart, developers can easily create and manage their applications, ensuring high performance and scalability. " \
        "Barclays has seen significant improvements in developer productivity and application performance since adopting the Dart platform.",
        headers={"Content-Type": "text/plain"},
    )
    return client


MOCK_AGENT_RESPONSE = {
    "answer": "Dart platform is used by Barclays front office developers.",
    "tool_calls": [
        {
            "tool": "search_document",
            "tool_input": {"keyword": "Dart"},
            "tool_output": "Dart platform is used by Barclays front office developers.",
        }
    ],
}

MOCK_STATS_RESPONSE = {
    "answer": "The document has 120 words.",
    "tool_calls": [
        {
            "tool": "document_stats",
            "tool_input": {},
            "tool_output": {"characters": 720, "words": 120, "lines": 5},
        }
    ],
}

MOCK_NO_TOOLS_RESPONSE = {
    "answer": "The document does not mention any budget information.",
    "tool_calls": [],
}

class TestAskQuestion:

    def test_no_document_returns_400(self, client):
        r = client.post("/questions", json={"question": "Who is the CEO of Barclays?"})
        assert r.status_code == 400

    def test_no_document_error_message(self, client):
        r = client.post("/questions", json={"question": "Who is the CEO of Barclays?"})
        assert "No document" in r.json()["detail"]

    def test_returns_200_with_document(self, client_with_doc):
        with patch("app.routes.document_qa.ask_agent", return_value=MOCK_AGENT_RESPONSE):
            r = client_with_doc.post("/questions", json={"question": "Who is the CEO of Barclays?"})
        assert r.status_code == 200

    def test_response_contains_answer(self, client_with_doc):
        with patch("app.routes.document_qa.ask_agent", return_value=MOCK_AGENT_RESPONSE):
            r = client_with_doc.post("/questions", json={"question": "What platform is used by Barclays?"})
        assert r.json()["answer"] == "Dart platform is used by Barclays front office developers."

    def test_response_contains_tool_calls(self, client_with_doc):
        with patch("app.routes.document_qa.ask_agent", return_value=MOCK_AGENT_RESPONSE):
            r = client_with_doc.post("/questions", json={"question": "What is Dart?"})
        tool_calls = r.json()["tool_calls"]
        assert isinstance(tool_calls, list)
        assert len(tool_calls) == 1
        assert tool_calls[0]["tool"] == "search_document"
        assert tool_calls[0]["tool_input"] == {"keyword": "Dart"}

    def test_tool_calls_empty_when_agent_uses_no_tools(self, client_with_doc):
        with patch("app.routes.document_qa.ask_agent", return_value=MOCK_NO_TOOLS_RESPONSE):
            r = client_with_doc.post("/questions", json={"question": "What is Dart's budget?"})
        assert r.json()["tool_calls"] == []
    
    def test_tool_calls_empty_when_agent_cant_find_information(self, client_with_doc):
        with patch("app.routes.document_qa.ask_agent", return_value=MOCK_NO_TOOLS_RESPONSE):
            r = client_with_doc.post("/questions", json={"question": "What is Dart's budget?"})
        assert r.json()["answer"] == "The document does not mention any budget information."

    def test_oversized_question_returns_422(self, client_with_doc):
        r = client_with_doc.post(
            "/questions",
            json={"question": "x" * (settings.MAX_QUESTION_CHARS + 1)},
        )
        assert r.status_code == 422

    def test_ask_agent_called_with_question_text(self, client_with_doc):
        with patch("app.routes.document_qa.ask_agent", return_value=MOCK_AGENT_RESPONSE) as mock:
            client_with_doc.post("/questions", json={"question": "Who is the CEO of Barclays?"})
        mock.assert_called_once_with("Who is the CEO of Barclays?")

    def test_missing_question_field_returns_422(self, client_with_doc):
        r = client_with_doc.post("/questions", json={})
        assert r.status_code == 422