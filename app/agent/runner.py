from typing import Any
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langsmith import traceable

from app.agent.tools import document_stats, read_document, search_document
from app.config import settings

SYSTEM_PROMPT = (
    "You are a document Q&A agent that answers questions about a document the user has uploaded.\n"
    "You have three tools:\n"
    "  - read_document: returns the full text. Use for general questions about content.\n"
    "  - document_stats: returns size info (chars/words/lines). Use for length/size questions.\n"
    "  - search_document: returns lines containing a keyword. Use for targeted lookups, "
    "especially in large documents.\n"
    "Pick the smallest tool that can answer the question. If the document does not contain the "
    "answer, just say you don't know."
)

_TOOLS = [read_document, document_stats, search_document]
_MAX_TOOL_OUTPUT_CHARS = 2_000


def build_agent(llm: BaseChatModel | None = None):
    """Build a compiled agent.

    Pass a custom ``llm`` to swap in a fake model for testing without making
    real API calls.  Omit it (or pass ``None``) to use the default
    ``ChatAnthropic`` configured via ``settings``.
    """
    model = llm or ChatAnthropic(model=settings.ANTHROPIC_MODEL, temperature=0)
    return create_agent(model, tools=_TOOLS, system_prompt=SYSTEM_PROMPT)


# Module-level default agent — used by the API at runtime.
_agent = build_agent()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _stringify(content: Any) -> str:
    """Normalise an LLM response to a plain string.

    ChatAnthropic can return content as a list of typed blocks, e.g.
    ``[{"type": "text", "text": "..."}]``.  Flatten to a single string.
    """
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)


def _truncate(text: str, limit: int = _MAX_TOOL_OUTPUT_CHARS) -> str:
    """Truncate tool output so it does not bloat the API response."""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n…[truncated, {len(text) - limit} more chars]"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@traceable(name="ask_agent", run_type="chain")
def ask_agent(question: str) -> dict[str, Any]:
    """Run the agent and return the final answer plus a trace of tool calls."""
    result = _agent.invoke({"messages": [{"role": "user", "content": question}]})
    messages = result["messages"]

    # Walk the message history to pair each AIMessage tool_call with its
    # corresponding ToolMessage response.
    steps: list[dict[str, Any]] = []
    for i, msg in enumerate(messages):
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_output = ""
                for subsequent in messages[i + 1:]:
                    if (
                        isinstance(subsequent, ToolMessage)
                        and subsequent.tool_call_id == tc["id"]
                    ):
                        tool_output = _truncate(str(subsequent.content))
                        break
                steps.append({
                    "tool": tc["name"],
                    "tool_input": tc["args"],
                    "tool_output": tool_output,
                })

    return {
        "answer": _stringify(messages[-1].content),
        "tool_calls": steps,
    }
