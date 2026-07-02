# Business Process Audit Tool

## What this is
An SME owner describes their business workflow in plain text; the tool returns
identified bottlenecks, specific AI tools to fix each one, estimated time saved,
and an implementation-difficulty rating.

Portfolio project. Judged on: end-to-end RAG, model benchmarking (RAG vs
no-RAG), and a clean production deployment. The README and the benchmark
results table are graded deliverables, not afterthoughts.

## Architecture
User input (workflow description)
  -> RAG retrieval (similar automation case studies, ChromaDB)
  -> Recommendation engine (API model, RAG-augmented or not)
  -> Structured output (bottlenecks + AI tools + time saved + difficulty)
  -> Streamlit UI  <->  FastAPI backend

## The key design rule
Every model variant lives behind ONE interface: `RecommendationEngine.generate(query, context)`
in `backend/llm/interface.py`. "API, no RAG" and "API, RAG-augmented" are just
implementations of that interface (see `ApiEngine.use_rag`). This makes the
benchmark a for-loop, not two rewrites. Do NOT scatter model calls through the
codebase — always go through the interface.

## Tech stack
- Python 3.11
- Backend: FastAPI + Pydantic (all I/O validated by Pydantic models)
- Vectors: ChromaDB (persistent), embeddings via sentence-transformers
- Frontend: Streamlit (calls the FastAPI endpoint over HTTP; no logic in the UI)
- LLM: Gemini API (`google-genai`), key read from env, never hardcoded

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
3. [x] ApiEngine: real API model with retrieved context, forced structured output
4. [x] Benchmark: RAG vs no-RAG on a 20-case rubric
5. [x] Deploy: Hugging Face Space (Docker SDK, backend + frontend in one container)
   Live: https://huggingface.co/spaces/tankaihooi/biz-audit-tool
6. [ ] Handle edge cases (empty/very short/non-business input)

## Commands
- Backend:  `uvicorn backend.main:app --reload --port 8000`
- Frontend: `streamlit run frontend/app.py`
- Install:  `pip install -r requirements.txt`

## Deployment
Single Hugging Face Space, Docker SDK (chosen over Render + Streamlit Cloud
after Render's 512MB free tier proved too tight for chromadb/sentence-transformers;
Spaces' free CPU tier gives 16GB). `Dockerfile` builds the Chroma index at
image-build time (Spaces disk isn't persistent). `start.sh` runs uvicorn
(internal, 127.0.0.1:8000) and streamlit (exposed, 0.0.0.0:7860) in one
container. README.md's YAML frontmatter is Hugging Face's required Space
config (sdk, app_port) — don't remove it.

## Gotchas to watch
- Normalize embeddings and match the distance metric to how vectors were created,
  or retrieval fails silently (returns plausible-but-wrong cases).
- Don't commit `.env` or the chroma persist dir.
- Validate every model output against the Pydantic schema before returning it;
  LLMs will occasionally break the JSON contract.
