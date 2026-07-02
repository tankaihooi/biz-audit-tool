"""Embed data/processed/case_studies.jsonl and persist it to ChromaDB.

Run once after data/processed changes:
    python -m scripts.ingest
"""

import json
from pathlib import Path

from backend.rag.store import get_retriever

CHUNKS_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "case_studies.jsonl"


def main() -> None:
    chunks = [json.loads(line) for line in CHUNKS_PATH.open(encoding="utf-8")]
    retriever = get_retriever()
    retriever.ingest(chunks)
    print(f"Ingested {len(chunks)} chunks into chroma_db/")


if __name__ == "__main__":
    main()
