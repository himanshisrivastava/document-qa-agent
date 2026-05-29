# Document Q&A Agent

A FastAPI service that lets you upload a plain-text document and ask questions about it. Questions are answered by a LangChain agent backed by Claude (Anthropic), which picks the right tool for each query rather than always reading the entire document.

---

## How it works

```
POST /documents  →  stores document.txt on disk
POST /questions  →  agent picks a tool → Claude answers → returns answer + tool trace
```

The agent has three tools:

| Tool | When it's used |
|---|---|
| `read_document` | General questions that need the full text |
| `search_document` | Targeted keyword lookups in large documents |
| `document_stats` | Questions about length, word count, or size |


## Setup

### Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)

### Install

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# LangSmith tracing (optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGCHAIN_PROJECT=doc-qa-api
```

---

## Running the API

```bash
uvicorn app.main:app --reload
```

The API is now available at `http://localhost:8000`.  
Interactive docs (Swagger UI): `http://localhost:8000/docs`

---

## API reference

### `POST /documents`

Upload a plain-text document. Subsequent uploads overwrite the previous one.

**Request**

```
Content-Type: text/plain

<your document text>
```

**Response** `201 Created`

```json
{
  "status": "success",
  "characters": 1042
}
```

**Limits:** 1 – 500,000 characters.

**Example (curl)**

```bash
curl -X POST http://localhost:8000/documents \
  -H "Content-Type: text/plain" \
  --data-binary @report.txt
```

Or with inline text:

```bash
curl -X POST http://localhost:8000/documents \
  -H "Content-Type: text/plain" \
  -d "ACME Q3 Report. Revenue was $42.3M. CEO is Sarah Chen."
```

---

### `POST /questions`

Ask a question about the uploaded document.

**Request**

```json
{
  "question": "Who is the CEO?"
}
```

**Response** `200 OK`

```json
{
  "answer": "Sarah Chen is the CEO of ACME.",
  "tool_calls": [
    {
      "tool": "search_document",
      "tool_input": { "keyword": "CEO" },
      "tool_output": "CEO is Sarah Chen."
    }
  ]
}
```

`tool_calls` shows exactly which tool the agent used and what it returned, so you can trace how the answer was derived.

**Limits:** 1 – 2,000 characters per question.

**Errors**

| Status | Meaning |
|---|---|
| `400` | No document uploaded yet |
| `422` | Validation error (empty question, question too long) |

**Example (curl)**

```bash
curl -X POST http://localhost:8000/questions \
  -H "Content-Type: application/json" \
  -d '{"question": "What was the Q3 revenue?"}'
```

---

## Running with Docker

### Docker Compose (recommended)

```bash
docker compose up --build
```

The document is stored in a named volume (`doc_storage`) so it survives container restarts.

### Docker directly

```bash
docker build -t doc-qa-api .
docker run -p 8000:8000 --env-file .env doc-qa-api
```

---

## Tests

Tests mock the LLM — no API key required.

```bash
pip install -r requirements-test.txt
pytest
```
---

## Evaluation (Ragas)

Runs the agent against a set of labelled examples and scores the answers with Claude as judge.

```bash
pip install -r requirements-eval.txt
python evals/run_eval.py
```

**Metrics**

| Metric | What it measures |
|---|---|
| `faithfulness` | Is the answer grounded in the retrieved context? |
| `answer_correctness` | Does the answer match the ground truth? |
| `context_precision` | Is the retrieved context relevant to the question? |
| `context_recall` | Does the retrieved context cover the ground truth? |

The dataset lives in `evals/dataset.json`. Add more `{ "name", "document", "question", "ground_truth" }` objects to extend it.

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | — | Anthropic API key |
| `DOCUMENT_DIR` | ❌ | Project root | Directory where `document.txt` is stored |
| `LANGCHAIN_TRACING_V2` | ❌ | `false` | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | ❌ | — | LangSmith API key (required if tracing enabled) |
| `LANGCHAIN_PROJECT` | ❌ | — | LangSmith project name |


## Improvements to be added
1. Chunking to data for large datasets
2. Storing the chunks in a vectordb 
3. Use embeddings for finding relevant chunks
4. Ability to upload more than one document
