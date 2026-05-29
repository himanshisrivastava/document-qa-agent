"""LLM tool definitions"""

from langchain_core.tools import tool
from app.config import settings


def _load_doc() -> str | None:
    """Return raw document text, or None if no document has been uploaded."""
    if not settings.document_path.exists():
        return None
    return settings.document_path.read_text(encoding="utf-8")


@tool
def read_document() -> str:
    """Return the full text of the currently uploaded document.

    Use for general questions about content where you need to read everything.
    """
    text = _load_doc()
    if text is None:
        return "No document has been uploaded yet"
    return text


@tool
def document_stats() -> dict:
    """Return size statistics for the document: character, word, and line counts.

    Use when the user asks about the document's length or size.
    """
    text = _load_doc()
    if text is None:
        return {"error": "No document has been uploaded yet"}
    return {
        "characters": len(text),
        "words": len(text.split()),
        "lines": text.count("\n") + 1,
    }


@tool
def search_document(keyword: str) -> str:
    """Return lines from the document containing the given keyword (case-insensitive).

    Use for answering specific questions about the document content. Use the keyword to find relevant sections of the document that may contain the answer.
    """
    text = _load_doc()
    if text is None:
        return "No document has been uploaded yet."
    word_lower = keyword.lower()
    matches = [line for line in text.splitlines() if word_lower in line.lower()]
    if not matches:
        return f"No lines containing '{keyword}' found."
    return "\n".join(matches[:10]) 
