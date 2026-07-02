"""Every model variant lives behind this one interface.

API-with-RAG and API-without-RAG are both just RecommendationEngine
implementations. This is what makes the benchmark a for-loop.
"""

import os
from abc import ABC, abstractmethod

from .schema import Recommendation, Bottleneck, Difficulty


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
    """A frontier API model, optionally prompted with retrieved context.

    Set use_rag=False to benchmark the model against its own RAG-augmented
    output (the 'no-RAG' baseline).

    TODO(step 3): call the API, force JSON matching the Recommendation schema,
    validate with Recommendation.model_validate_json before returning.
    """

    def __init__(self, use_rag: bool = True) -> None:
        self.api_key = os.environ["LLM_API_KEY"]
        self.use_rag = use_rag

    def generate(self, query: str, context: list[str]) -> Recommendation:
        raise NotImplementedError("Implement in step 3.")


def get_engine(name: str | None = None) -> RecommendationEngine:
    """Factory driven by the ENGINE env var (or an explicit name for benchmarking)."""
    name = name or os.getenv("ENGINE", "stub")
    return {
        "stub": StubEngine,
        "api": lambda: ApiEngine(use_rag=True),
        "api_no_rag": lambda: ApiEngine(use_rag=False),
    }[name]()
