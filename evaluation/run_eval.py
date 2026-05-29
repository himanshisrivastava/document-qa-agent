"""Ragas evaluation for the Document Q&A agent.

Loads dataset.json, runs each question through the agent, then scores
the answers with Claude as the judge LLM.

Run with:
    python evals/run_eval.py

Requires:
    pip install -r requirements-eval.txt
    ANTHROPIC_API_KEY set in .env or the environment
"""

# ---------------------------------------------------------------------------
# Compatibility shim — must run before any ragas import.
# ragas 0.2.x tries to import removed VertexAI/Palm symbols from
# langchain_community 0.3+. These stubs prevent the ImportError; they are
# never actually called because we supply our own Claude judge LLM.
# ---------------------------------------------------------------------------
import importlib
import sys
from types import ModuleType


class _DynamicStub(ModuleType):
    def __getattr__(self, name: str) -> type:
        dummy = type(name, (), {"__module__": self.__name__})
        setattr(self, name, dummy)
        return dummy


def _stub(path: str) -> None:
    if path in sys.modules:
        return
    for depth in range(1, len(path.split("."))):
        parent = ".".join(path.split(".")[:depth])
        if parent not in sys.modules:
            try:
                importlib.import_module(parent)
            except ImportError:
                sys.modules[parent] = ModuleType(parent)
    sys.modules[path] = _DynamicStub(path)


def _patch(path: str) -> None:
    try:
        mod = importlib.import_module(path)
    except ImportError:
        _stub(path)
        return
    if not getattr(mod, "__getattr__", None):
        def _fallback(name: str) -> type:
            dummy = type(name, (), {"__module__": path})
            setattr(mod, name, dummy)
            return dummy
        mod.__getattr__ = _fallback  # type: ignore[attr-defined]


for _p in ["langchain_community.chat_models.vertexai", "langchain_community.chat_models.google_palm"]:
    _stub(_p)
for _p in ["langchain_community.llms", "langchain_community.chat_models", "langchain_community.embeddings"]:
    _patch(_p)
# ---------------------------------------------------------------------------

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
os.environ.setdefault("LANGCHAIN_PROJECT", "document-qa-agent-api-evals")

from app.agent.runner import ask_agent
from app.config import settings
from datasets import Dataset
from langchain_anthropic import ChatAnthropic
from ragas import evaluate
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import answer_correctness, context_precision, context_recall, faithfulness

DATASET_PATH = Path(__file__).parent / "dataset.json"


def run() -> None:
    examples = json.loads(DATASET_PATH.read_text())
    print(f"Running {len(examples)} example(s)…\n")

    rows = []
    for ex in examples:
        settings.document_path.write_text(ex["document"], encoding="utf-8")
        result = ask_agent(ex["question"])
        contexts = [tc["tool_output"] for tc in result["tool_calls"]] or [ex["document"]]
        rows.append({
            "question": ex["question"],
            "answer": result["answer"],
            "contexts": contexts,
            "ground_truth": ex["ground_truth"],
        })

    judge = LangchainLLMWrapper(ChatAnthropic(model=settings.ANTHROPIC_MODEL, temperature=0))
    answer_correctness.weights = [1, 0]  # LLM-only; no embeddings needed

    report = evaluate(
        Dataset.from_list(rows),
        metrics=[faithfulness, answer_correctness, context_precision, context_recall],
        llm=judge,
    )

    df = report.to_pandas()
    print(df.to_string(index=False))
    print()
    for col in df.select_dtypes(include="number").columns:
        print(f"{col}: {df[col].mean():.3f}")


if __name__ == "__main__":
    run()
