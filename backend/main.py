"""FastAPI backend. Wraps: retrieve context -> engine.generate -> structured output."""

from dotenv import load_dotenv
from fastapi import FastAPI

from backend.llm.interface import get_engine
from backend.llm.schema import AuditRequest, Recommendation
from backend.rag.store import get_retriever

load_dotenv()

app = FastAPI(title="Business Process Audit Tool")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/recommend", response_model=Recommendation)
def recommend(req: AuditRequest) -> Recommendation:
    """The full pipeline: query -> RAG context -> engine -> structured recommendation."""
    context = get_retriever().retrieve(req.workflow_description)  # empty until step 2
    engine = get_engine()  # driven by ENGINE env var; 'stub' by default
    return engine.generate(req.workflow_description, context)
