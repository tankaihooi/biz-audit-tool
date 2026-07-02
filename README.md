# Business Process Audit Tool

An SME owner describes their business workflow; the tool returns identified
bottlenecks, specific AI tools to address each, estimated time saved, and an
implementation-difficulty rating. Built on a RAG + fine-tuned-LLM pipeline.

> Portfolio project demonstrating end-to-end RAG, QLoRA fine-tuning, model
> benchmarking, and production deployment.

## Demo
<!-- TODO: screenshot or GIF of the UI, and the live Hugging Face Spaces link -->

## Architecture
```
Workflow description
  -> RAG retrieval (ChromaDB over automation case studies)
  -> Recommendation engine (API model | fine-tuned | fine-tuned + RAG)
  -> Structured output (bottlenecks + AI tools + time saved + difficulty)
  -> Streamlit UI  <->  FastAPI backend
```
All model variants sit behind one interface (`backend/llm/interface.py`), so
swapping engines — and benchmarking them — is trivial.

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in LLM_API_KEY; ENGINE=stub works with no key

uvicorn backend.main:app --reload --port 8000   # terminal 1
streamlit run frontend/app.py                    # terminal 2
```

## Benchmark results
<!-- TODO: the headline table. API vs fine-tuned vs fine-tuned+RAG, scored on
relevance / specificity / actionability (1-5) across 20 test cases. Include an
honest read of what won and why — even if fine-tuning lost to RAG-only. -->

| Variant | Relevance | Specificity | Actionability | Mean |
|---|---|---|---|---|
| GPT-4o (no RAG) | | | | |
| Fine-tuned | | | | |
| Fine-tuned + RAG | | | | |

## How the fine-tuning was done
<!-- TODO: QLoRA on Mistral 7B / Llama 3 8B, Kaggle GPU, dataset construction,
hyperparameters, what you'd change. -->

## What I'd do differently
<!-- TODO: honest reflection. This section reads well in interviews. -->
