# Business Process Audit Tool

## What this is
An SME owner describes their business workflow in plain text; the tool returns
identified bottlenecks, specific AI tools to fix each one, estimated time saved,
and an implementation-difficulty rating.

Portfolio project. Judged on: end-to-end RAG, QLoRA fine-tuning, model
benchmarking, and a clean production deployment. The README and the benchmark
results table are graded deliverables, not afterthoughts.

## Architecture
User input (workflow description)
  -> RAG retrieval (similar automation case studies, ChromaDB)
  -> Recommendation engine (API model, or fine-tuned model, or fine-tuned + RAG)
  -> Structured output (bottlenecks + AI tools + time saved + difficulty)
  -> Streamlit UI  <->  FastAPI backend

## The key design rule
Every model variant lives behind ONE interface: `RecommendationEngine.generate(query, context)`
in `backend/llm/interface.py`. "Vanilla API", "fine-tuned", and "fine-tuned + RAG"
are just implementations of that interface. This makes the Week-4 benchmark a for-loop,
not three rewrites. Do NOT scatter model calls through the codebase — always go
through the interface.

## Tech stack
- Python 3.11
- Backend: FastAPI + Pydantic (all I/O validated by Pydantic models)
- Vectors: ChromaDB (persistent), embeddings via sentence-transformers
- Frontend: Streamlit (calls the FastAPI endpoint over HTTP; no logic in the UI)
- Fine-tuning: QLoRA on Mistral 7B / Llama 3 8B, done on Kaggle GPU (separate env,
  see notebooks/ — do NOT add training deps to the main requirements.txt)
- API baseline model: read the key from env, never hardcode

## Conventions
- Structured output is the `Recommendation` Pydantic model in `backend/llm/schema.py`.
  Never return free-form text to the frontend.
- Secrets in `.env` only, loaded via python-dotenv. `.env` is gitignored.
- Type hints everywhere. Docstrings on public functions.
- Keep the frontend dumb: it sends a string, renders a `Recommendation`. All
  intelligence is server-side.

## Build order (current status)
1. [x] Walking skeleton: Streamlit -> FastAPI -> hardcoded Recommendation (StubEngine)
2. [x] RAG: ingest/chunk case studies, embed, ChromaDB, test retrieval
3. [ ] ApiEngine: real API model with retrieved context, forced structured output
4. [ ] QLoRA fine-tuning on Kaggle -> FinetunedEngine (swappable backend)
5. [ ] Benchmark: API vs fine-tuned vs fine-tuned+RAG on a 20-case rubric
6. [ ] Deploy on Hugging Face Spaces; handle edge cases (empty/very short/non-business input)

## Commands
- Backend:  `uvicorn backend.main:app --reload --port 8000`
- Frontend: `streamlit run frontend/app.py`
- Install:  `pip install -r requirements.txt`

## Gotchas to watch
- Normalize embeddings and match the distance metric to how vectors were created,
  or retrieval fails silently (returns plausible-but-wrong cases).
- Don't commit `.env`, the chroma persist dir, or model weights.
- Validate every model output against the Pydantic schema before returning it;
  LLMs will occasionally break the JSON contract.
