from pydantic import BaseModel, Field
from app.config import settings


class DocumentOut(BaseModel):
    status: str
    characters: int

class QuestionIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=settings.MAX_QUESTION_CHARS)

class ToolCall(BaseModel):
    tool: str
    tool_input: dict | str | None = None
    tool_output: str

class QuestionOut(BaseModel):
    answer: str
    tool_calls: list[ToolCall] = []
