from typing import Annotated
from fastapi import APIRouter, Body, HTTPException
from app.agent.runner import ask_agent
from app.config import settings
from app.models.model import DocumentOut, QuestionIn, QuestionOut

router = APIRouter()

@router.post("/documents", response_model=DocumentOut, status_code=201)
def upload_document(
    text: Annotated[
        str,
        Body(
            media_type="text/plain",
            min_length=1,
            max_length=settings.MAX_DOCUMENT_CHARS,
        ),
    ],
) -> DocumentOut:
    """Upload a document for the agent to answer questions about"""
    settings.document_path.write_text(text, encoding="utf-8")
    return DocumentOut(status="success", characters=len(text))


@router.post("/questions", response_model=QuestionOut)
def ask_question(payload: QuestionIn) -> QuestionOut:
    """Ask a question about the uploaded document
    Returns the agent's answer plus a trace of every tool call it made
    Raises 400 if no document has been uploaded yet
    """
    if not settings.document_path.exists():
        raise HTTPException(
            status_code=400,
            detail="No document uploaded yet. Upload a document text first using POST call /documents first",
        )
    return QuestionOut(**ask_agent(payload.question))
