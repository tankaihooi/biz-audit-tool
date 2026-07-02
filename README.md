# Business Process Audit Tool

An SME owner describes their business workflow; the tool returns identified
bottlenecks, specific AI tools to address each, estimated time saved, and an
implementation-difficulty rating. Built on a RAG-augmented LLM pipeline.

> Portfolio project demonstrating end-to-end RAG, model benchmarking, and
> production deployment.

## Demo
**Live:** https://huggingface.co/spaces/tankaihooi/biz-audit-tool
<!-- TODO: screenshot or GIF of the UI -->

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

## Deployment
Single [Hugging Face Space](https://huggingface.co/spaces) (Docker SDK). The
`Dockerfile` builds the Chroma index at image-build time (Spaces disk isn't
persistent) and `start.sh` runs both processes in one container: FastAPI
backend bound to `127.0.0.1:8000` internally, Streamlit frontend on the
exposed `0.0.0.0:7860`, talking to each other over `BACKEND_URL` exactly like
local dev.

To deploy: create a Space with the Docker SDK, push this repo to it, and set
`GEMINI_API_KEY` as a Space secret (Settings → Repository secrets — not
stored in the repo). Hugging Face reads Space config (SDK type, exposed
port) from YAML frontmatter at the very top of this file — if it's ever
missing, add it back before pushing or the Docker SDK won't be detected:
```yaml
---
title: Business Process Audit Tool
sdk: docker
app_port: 7860
---
```

## Benchmark results
Same Gemini 2.5 Flash model, no RAG vs RAG-augmented, scored by an LLM judge
(`gemini-2.5-flash-lite`, kept off the model being benchmarked) on relevance /
specificity / actionability (1-5) across 20 test cases
(`data/eval/test_cases.json`). Reproduce with `python -m scripts.benchmark`;
raw per-case outputs land in `data/eval/benchmark_results.jsonl`.

| Variant | Relevance | Specificity | Actionability | Mean |
|---|---|---|---|---|
| Gemini 2.5 Flash (no RAG) | 4.90 | 4.15 | 3.75 | 4.27 |
| Gemini 2.5 Flash (RAG-augmented) | 4.95 | 4.10 | 3.35 | 4.13 |

**Honest read: RAG lost, on this corpus.** Both variants tie on relevance,
but RAG-augmented scores meaningfully lower on actionability (3.35 vs 3.75)
and slightly lower on specificity. Splitting the 20 cases into ones that
resemble the RAG corpus's actual content (Microsoft Power Platform
enterprise deployments — banks, insurers, global logistics firms) versus 5
cases I deliberately wrote as small/generic businesses (a bakery, a gym, a
landscaper, a freelance photographer) shows why:

| Segment | Variant | Specificity | Actionability |
|---|---|---|---|
| Enterprise-like (15 cases) | no RAG | 4.27 | 3.87 |
| Enterprise-like (15 cases) | RAG | 4.13 | 3.40 |
| Small/generic (5 cases) | no RAG | 3.80 | 3.40 |
| Small/generic (5 cases) | RAG | 4.00 | 3.20 |

RAG not only failed to help on the mismatched small-business cases, it
underperforms even on the cases closest to its own corpus. Reading the raw
outputs explained why: retrieved context nudged the model toward naming more
tools per bottleneck, often specific Microsoft Power Platform products
(Power Automate, AI Builder, Dataverse), rather than fewer, better-targeted
picks. On `invoice-reentry`, the no-RAG answer named 3 tools; RAG-augmented
named 7. On `bakery-ordering`, RAG suggested "custom Python scripts using
libraries like Prophet or ARIMA" where no-RAG suggested off-the-shelf
"AI-powered inventory management" software, which is objectively less actionable
for a non-technical owner, and a direct artifact of grounding a five-person
bakery's workflow in case studies about enterprise deployments. The key takeaway from
this isn't "RAG doesn't work" however — it's that retrieval quality is bounded by corpus
relevance, and a corpus of large-company automation stories doesn't
transfer well to genuinely small businesses even though it's nominally
about "AI automation case studies." A corpus curated at SME scale would be
the natural next experiment.

One calibration caveat: relevance scores are tightly clustered near the top
(4.90-4.95) across almost all 40 runs, which suggests the LLM judge may be
lenient/uncalibrated on that dimension rather than genuinely unable to
discriminate — specificity and actionability show more spread and are
probably the more trustworthy signal here.

## What I'd do differently
- **Curate the RAG corpus for the actual target user, not the nearest available dataset.**
  I built the corpus from Microsoft's published Power Platform case studies because they were
  well-structured and easy to scrape, but they're enterprise deployment stories, and this tool
  is aimed at SMEs. The benchmark caught the mismatch directly: RAG underperformed no-RAG on
  actionability precisely because it kept grounding small-business workflows in enterprise
  tooling. I'd either source or write case studies at the actual scale of the target user before
  building the retrieval pipeline, not after.
- **Design the eval harness around free-tier quota limits from day one.** Gemini's free tier caps
  generation at ~20 requests/day/model — I discovered this mid-benchmark, not while planning it,
  and ended up bolting on resumability, multi-key rotation, and retry/backoff logic after the
  fact. All of that should have been the starting design, not a patch.
- **Add a startup log line showing which engine is actually active.** `ENGINE` silently defaults
  to `stub` if unset, and the deployed Space ran on the hardcoded stub output for a while before
  anyone noticed the recommendations weren't changing per input. A one-line "Engine: api (RAG=on)"
  log at startup would have caught that in seconds instead of requiring a user to notice a pattern.
- **Exercise the UI with realistic, varied model output earlier.** Several bugs only showed up
  once real Gemini output (not the hardcoded stub) hit the frontend: the model converging on
  exactly 2 bottlenecks with no stated reason not to, full-sentence tool descriptions breaking a
  comma-joined list, and long descriptions overflowing a UI element sized for short labels. All
  were quick fixes, but all were invisible until real usage surfaced them.
- **Sanity-check the LLM judge's calibration.** Relevance scores clustered at 4.9-5.0 across
  nearly every case, which is more consistent with a lenient judge than with genuinely uniform
  quality. I'd add a couple of deliberately weak/irrelevant recommendations to the eval set as a
  calibration check. If the judge doesn't mark those down clearly, the scale isn't discriminating
  and the numbers are less trustworthy than they look.
