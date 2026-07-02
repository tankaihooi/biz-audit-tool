# Business Process Audit Tool

An SME owner describes their business workflow; the tool returns identified
bottlenecks, specific AI tools to address each, estimated time saved, and an
implementation-difficulty rating. Built on a RAG-augmented LLM pipeline.

> Portfolio project demonstrating end-to-end RAG, model benchmarking, and
> production deployment.

## Demo
<!-- TODO: screenshot or GIF of the UI, and the live Hugging Face Spaces link -->

## Architecture
```
Workflow description
  -> RAG retrieval (ChromaDB over automation case studies)
  -> Recommendation engine (API model, RAG-augmented or not)
  -> Structured output (bottlenecks + AI tools + time saved + difficulty)
  -> Streamlit UI  <->  FastAPI backend
```
All model variants sit behind one interface (`backend/llm/interface.py`), so
swapping engines — and benchmarking them — is trivial.

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in GEMINI_API_KEY; ENGINE=stub works with no key

uvicorn backend.main:app --reload --port 8000   # terminal 1
streamlit run frontend/app.py                    # terminal 2
```

## Benchmark results
Same Gemini 2.5 Flash model, no RAG vs RAG-augmented, scored by an LLM judge
on relevance / specificity / actionability (1-5) across 20 test cases
(`data/eval/test_cases.json`). Reproduce with `python -m scripts.benchmark`;
raw per-case outputs land in `data/eval/benchmark_results.jsonl`.
<!-- TODO: honest read of what RAG bought (or didn't) and why. -->

| Variant | Relevance | Specificity | Actionability | Mean |
|---|---|---|---|---|
| Gemini 2.5 Flash (no RAG) | | | | |
| Gemini 2.5 Flash (RAG-augmented) | | | | |

## What I'd do differently
<!-- TODO: honest reflection. This section reads well in interviews. -->
