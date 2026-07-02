"""Every model variant lives behind this one interface.

API-with-RAG and API-without-RAG are both just RecommendationEngine
implementations. This is what makes the benchmark a for-loop.
"""

import os
from abc import ABC, abstractmethod

from google import genai
from google.genai import types

from .schema import Recommendation, Bottleneck, Difficulty

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = """\
You are a business process automation consultant. A small or medium-sized \
business owner describes one of their workflows in plain language. Identify \
the concrete bottlenecks in that workflow and, for each one, recommend \
specific AI tools that would fix it (not generic advice like "use AI more"), \
a realistic estimate of time saved, and how hard it would be to implement."""


class RecommendationEngine(ABC):
    """Contract for anything that turns a workflow + context into a Recommendation."""

    @abstractmethod
    def generate(self, query: str, context: list[str]) -> Recommendation:
        """query = workflow description; context = retrieved case-study chunks."""
        ...


class StubEngine(RecommendationEngine):
    """Hardcoded output. Used for the walking skeleton and as a fast UI/test fixture."""

    def generate(self, query: str, context: list[str]) -> Recommendation:
        return Recommendation(
            summary="Manual, repetitive steps dominate this workflow.",
            bottlenecks=[
                Bottleneck(
                    description="Staff manually copy order data between email and the ERP.",
                    ai_tools=["Document AI / OCR", "RPA (Power Automate)"],
                    estimated_time_saved="5-8 hours/week",
                    implementation_difficulty=Difficulty.medium,
                ),
                Bottleneck(
                    description="Customer queries are answered ad hoc with no triage.",
                    ai_tools=["LLM support assistant with RAG over past tickets"],
                    estimated_time_saved="3-4 hours/week",
                    implementation_difficulty=Difficulty.low,
                ),
            ],
        )


class ApiEngine(RecommendationEngine):
    """Gemini API model, optionally prompted with retrieved context.

    Set use_rag=False to benchmark the model against its own RAG-augmented
    output (the 'no-RAG' baseline).
    """

    def __init__(self, use_rag: bool = True, model: str | None = None) -> None:
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.model = model or os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        self.use_rag = use_rag

    def generate(self, query: str, context: list[str]) -> Recommendation:
        prompt = self._build_prompt(query, context if self.use_rag else [])
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=Recommendation,
            ),
        )
        # The API is prompted for schema-shaped JSON, but LLMs occasionally
        # break the contract — always validate before returning.
        return Recommendation.model_validate_json(response.text)

    def _build_prompt(self, query: str, context: list[str]) -> str:
        parts = [f"Workflow description:\n{query}"]
        if context:
            case_studies = "\n\n---\n\n".join(context)
            parts.append(f"Similar automation case studies for reference:\n{case_studies}")
        return "\n\n".join(parts)


def get_engine(name: str | None = None) -> RecommendationEngine:
    """Factory driven by the ENGINE env var (or an explicit name for benchmarking)."""
    name = name or os.getenv("ENGINE", "stub")
    return {
        "stub": StubEngine,
        "api": lambda: ApiEngine(use_rag=True),
        "api_no_rag": lambda: ApiEngine(use_rag=False),
    }[name]()
