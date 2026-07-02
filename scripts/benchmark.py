"""Benchmark ApiEngine: RAG-augmented vs no-RAG, scored by an LLM judge.

Runs data/eval/test_cases.json through both variants, scores each output on
relevance/specificity/actionability with Gemini as judge, and writes raw
results plus a summary table.

Gemini's free tier caps generation at a small number of requests per day,
per model/project - not just per minute. This script is resumable: it skips
(case, variant) pairs already recorded in benchmark_results.jsonl, and stops
cleanly (instead of retrying forever) when it detects the daily cap has been
hit, so you can just re-run it once the quota resets.

To finish in one sitting instead of waiting for daily resets, set
GEMINI_API_KEYS to a comma-separated list of keys (each gets its own quota
bucket) - the script rotates to the next one when the current key taps out.
Falls back to a single GEMINI_API_KEY if GEMINI_API_KEYS isn't set.

Usage: python -m scripts.benchmark
"""

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field

from backend.llm.interface import get_engine
from backend.llm.schema import Recommendation
from backend.rag.store import get_retriever

load_dotenv()

TEST_CASES_PATH = Path(__file__).resolve().parent.parent / "data" / "eval" / "test_cases.json"
RESULTS_PATH = Path(__file__).resolve().parent.parent / "data" / "eval" / "benchmark_results.jsonl"

API_KEYS = [
    k.strip()
    for k in os.environ.get("GEMINI_API_KEYS", os.environ.get("GEMINI_API_KEY", "")).split(",")
    if k.strip()
]
if not API_KEYS:
    raise RuntimeError("Set GEMINI_API_KEY or GEMINI_API_KEYS in .env")

VARIANTS = ["api_no_rag", "api"]
VARIANT_LABELS = {
    "api_no_rag": "Gemini 2.5 Flash (no RAG)",
    "api": "Gemini 2.5 Flash (RAG-augmented)",
}

# Judging uses a different model than the one being benchmarked so it draws
# from a separate daily quota bucket instead of competing with it.
JUDGE_MODEL = "gemini-2.5-flash-lite"

MAX_RETRIES = 7
BASE_BACKOFF_SECONDS = 15
MAX_BACKOFF_SECONDS = 120


class DailyQuotaExceeded(Exception):
    pass


class JudgeScore(BaseModel):
    relevance: int = Field(
        ..., ge=1, le=5, description="Are the identified bottlenecks actually present in the workflow?"
    )
    specificity: int = Field(
        ..., ge=1, le=5, description="Are the recommended AI tools concrete, not generic advice?"
    )
    actionability: int = Field(
        ..., ge=1, le=5, description="Could a non-technical SME owner act on this without further research?"
    )
    rationale: str = Field(..., description="One or two sentences justifying the scores.")


JUDGE_INSTRUCTION = """\
You are grading an AI business-process-audit tool's output. Given a workflow \
description and its generated recommendation, score the recommendation on three \
1-5 scales: relevance, specificity, and actionability. Be a strict, consistent \
grader across cases - reserve 5s for genuinely excellent output."""


RETRYABLE_CODES = {429, 500, 503}


def call_with_retry(fn, *args, **kwargs):
    """Retry on rate limits and transient server errors; fail fast (no point
    backing off) once the daily cap is hit."""
    for attempt in range(MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except errors.APIError as e:
            if e.code == 429 and "PerDay" in str(e):
                raise DailyQuotaExceeded(str(e)) from e
            if e.code not in RETRYABLE_CODES or attempt == MAX_RETRIES - 1:
                raise
            wait = min(BASE_BACKOFF_SECONDS * (2**attempt), MAX_BACKOFF_SECONDS)
            print(f"    {e.code} error, retrying in {wait}s...")
            time.sleep(wait)


def judge(client: genai.Client, workflow: str, recommendation: Recommendation) -> JudgeScore:
    prompt = (
        f"Workflow description:\n{workflow}\n\n"
        f"Generated recommendation:\n{recommendation.model_dump_json(indent=2)}"
    )
    response = call_with_retry(
        client.models.generate_content,
        model=JUDGE_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=JUDGE_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=JudgeScore,
        ),
    )
    return JudgeScore.model_validate_json(response.text)


def load_existing_results() -> dict[tuple[str, str], dict]:
    if not RESULTS_PATH.exists():
        return {}
    records = (json.loads(line) for line in RESULTS_PATH.read_text().splitlines() if line.strip())
    return {(r["case_id"], r["variant"]): r for r in records}


def build_clients(key: str) -> tuple[dict, genai.Client]:
    os.environ["GEMINI_API_KEY"] = key
    engines = {name: get_engine(name) for name in VARIANTS}
    return engines, genai.Client(api_key=key)


def run() -> None:
    test_cases = json.loads(TEST_CASES_PATH.read_text())
    retriever = get_retriever()

    key_idx = 0
    engines, judge_client = build_clients(API_KEYS[key_idx])

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = load_existing_results()
    if existing:
        print(f"Resuming: {len(existing)} pairs already scored in {RESULTS_PATH}")

    keys_exhausted = False
    with RESULTS_PATH.open("a", encoding="utf-8") as out:
        for case in test_cases:
            if keys_exhausted:
                break
            pending = [v for v in VARIANTS if (case["id"], v) not in existing]
            if not pending:
                continue

            context = retriever.retrieve(case["workflow_description"])
            for variant in pending:
                recommendation = score = None
                while True:
                    try:
                        recommendation = call_with_retry(
                            engines[variant].generate, case["workflow_description"], context
                        )
                        score = judge(judge_client, case["workflow_description"], recommendation)
                        break
                    except DailyQuotaExceeded:
                        key_idx += 1
                        if key_idx >= len(API_KEYS):
                            print(
                                "\nAll API keys hit today's daily cap. Progress is saved - "
                                "re-run `python -m scripts.benchmark` once more quota is "
                                "available to pick up where this left off."
                            )
                            keys_exhausted = True
                            break
                        print(f"    key {key_idx} exhausted, rotating to key {key_idx + 1}/{len(API_KEYS)}...")
                        engines, judge_client = build_clients(API_KEYS[key_idx])
                if keys_exhausted:
                    break

                record = {
                    "case_id": case["id"],
                    "industry": case["industry"],
                    "variant": variant,
                    "recommendation": recommendation.model_dump(),
                    "score": score.model_dump(),
                }
                existing[(case["id"], variant)] = record
                out.write(json.dumps(record) + "\n")
                out.flush()
                print(
                    f"  {case['id']:<22} {variant:<12} "
                    f"rel={score.relevance} spec={score.specificity} act={score.actionability}"
                )
            if keys_exhausted:
                break

    total_pairs = len(test_cases) * len(VARIANTS)
    print(f"\n{len(existing)}/{total_pairs} pairs scored.")
    if len(existing) < total_pairs and not keys_exhausted:
        print("Some pairs are still missing - re-run the script to fill them in.")
    print_summary(list(existing.values()))


def print_summary(results: list[dict]) -> None:
    print("\n| Variant | Relevance | Specificity | Actionability | Mean |")
    print("|---|---|---|---|---|")
    for variant in VARIANTS:
        rows = [r["score"] for r in results if r["variant"] == variant]
        if not rows:
            print(f"| {VARIANT_LABELS[variant]} | - | - | - | - |")
            continue
        rel = sum(r["relevance"] for r in rows) / len(rows)
        spec = sum(r["specificity"] for r in rows) / len(rows)
        act = sum(r["actionability"] for r in rows) / len(rows)
        mean = (rel + spec + act) / 3
        print(f"| {VARIANT_LABELS[variant]} ({len(rows)} cases) | {rel:.2f} | {spec:.2f} | {act:.2f} | {mean:.2f} |")


if __name__ == "__main__":
    run()
