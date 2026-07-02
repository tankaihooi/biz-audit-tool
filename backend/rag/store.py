"""RAG retrieval over automation case studies.

Step 2 fills this in:
  1. Load case studies from data/processed/
  2. Chunk them
  3. Embed with sentence-transformers (normalize the vectors)
  4. Persist to ChromaDB
  5. retrieve(query) returns the top-k most similar chunks
"""

from functools import lru_cache


class CaseStudyRetriever:
    def __init__(self, persist_dir: str = "chroma_db", top_k: int = 4) -> None:
        self.persist_dir = persist_dir
        self.top_k = top_k
        # TODO(step 2): init chromadb.PersistentClient + embedding function

    def ingest(self, docs: list[str]) -> None:
        """Chunk, embed, and store case studies. Run once (or when data changes)."""
        raise NotImplementedError("Implement in step 2.")

    def retrieve(self, query: str) -> list[str]:
        """Return the top-k most relevant case-study chunks for a query."""
        # TODO(step 2): real similarity search
        return []


@lru_cache(maxsize=1)
def get_retriever() -> CaseStudyRetriever:
    return CaseStudyRetriever()
