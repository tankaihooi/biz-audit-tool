"""RAG retrieval over automation case studies.

Chunks live in data/processed/case_studies.jsonl (built by
scripts/build_case_study_chunks.py). ingest() embeds and persists them to
ChromaDB; retrieve(query) returns the top-k most similar chunks as context
for the recommendation engine.
"""

from functools import lru_cache
from typing import TypedDict

import chromadb
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "case_studies"


class CaseStudyChunk(TypedDict):
    id: str
    text: str
    title: str
    section: str
    source_url: str


class CaseStudyRetriever:
    def __init__(
        self,
        persist_dir: str = "chroma_db",
        top_k: int = 4,
        model_name: str = EMBEDDING_MODEL,
    ) -> None:
        self.top_k = top_k
        self._model = SentenceTransformer(model_name)
        self._client = chromadb.PersistentClient(path=persist_dir)
        # Cosine distance must match how embeddings are created: normalized
        # vectors + cosine space, or similarity search silently misranks results.
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def ingest(self, chunks: list[CaseStudyChunk]) -> None:
        """Embed and upsert pre-chunked case studies. Run once (or when data changes)."""
        if not chunks:
            return

        texts = [c["text"] for c in chunks]
        embeddings = self._model.encode(texts, normalize_embeddings=True).tolist()
        self._collection.upsert(
            ids=[c["id"] for c in chunks],
            embeddings=embeddings,
            documents=texts,
            metadatas=[
                {"title": c["title"], "section": c["section"], "source_url": c["source_url"]}
                for c in chunks
            ],
        )

    def retrieve(self, query: str) -> list[str]:
        """Return the top-k most relevant case-study chunks for a query."""
        if self._collection.count() == 0:
            return []

        query_embedding = self._model.encode([query], normalize_embeddings=True).tolist()
        results = self._collection.query(
            query_embeddings=query_embedding,
            n_results=min(self.top_k, self._collection.count()),
        )
        return results["documents"][0]


@lru_cache(maxsize=1)
def get_retriever() -> CaseStudyRetriever:
    return CaseStudyRetriever()
