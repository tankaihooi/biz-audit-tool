"""Structured output contract. The whole app speaks in these types."""

from enum import Enum
from pydantic import BaseModel, Field


class Difficulty(str, Enum):
    low = "Low"
    medium = "Medium"
    high = "High"


class Bottleneck(BaseModel):
    """A single identified bottleneck and how to address it."""

    description: str = Field(..., description="The bottleneck in the user's workflow.")
    ai_tools: list[str] = Field(
        ..., description="Specific AI tools/approaches that address this bottleneck."
    )
    estimated_time_saved: str = Field(
        ..., description="Human-readable estimate, e.g. '4-6 hours/week'."
    )
    implementation_difficulty: Difficulty


class Recommendation(BaseModel):
    """The full response returned to the frontend."""

    summary: str = Field(..., description="One-line read on the workflow.")
    bottlenecks: list[Bottleneck]


class AuditRequest(BaseModel):
    workflow_description: str = Field(..., min_length=1)
