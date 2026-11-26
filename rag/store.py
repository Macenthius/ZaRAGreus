"""Chroma persistent vector store wrapper (cosine space, embeddings passed explicitly)."""
from __future__ import annotations

import logging
from pathlib import Path

import chromadb
import numpy as np

import config
from rag.chunking import Chunk

log = logging.getLogger(__name__)


class VectorStore:
    """Stores chunk embeddings + metadata and answers nearest-neighbour queries."""

    def __init__(self, path: Path = config.CHROMA_DIR, name: str = config.COLLECTION_NAME) -> None:
        self.client = chromadb.PersistentClient(path=str(path))
        self.name = name
        self.collection = self.client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})

    def reset(self) -> None:
        """Drop and recreate the collection (makes index builds idempotent)."""
        try:
            self.client.delete_collection(self.name)
        except Exception:  # collection may not exist yet
            pass
        self.collection = self.client.create_collection(self.name, metadata={"hnsw:space": "cosine"})

    def add(self, chunks: list[Chunk], embeddings: np.ndarray, batch: int = 500) -> None:
        """Insert chunks in batches."""
        for i in range(0, len(chunks), batch):
            part = chunks[i:i + batch]
            self.collection.add(
                ids=[c.chunk_id for c in part],
                documents=[c.text for c in part],
                metadatas=[c.metadata for c in part],
                embeddings=embeddings[i:i + batch].tolist(),
            )

    def count(self) -> int:
        return self.collection.count()

    def all_chunks(self) -> list[Chunk]:
        """Load every stored chunk (used to build the in-memory BM25 index)."""
        got = self.collection.get(include=["documents", "metadatas"])
        return [Chunk(i, d, m) for i, d, m in zip(got["ids"], got["documents"], got["metadatas"])]

    def query(self, embedding: np.ndarray, n: int) -> list[tuple[str, float]]:
        """Return [(chunk_id, cosine_similarity)] best first."""
        res = self.collection.query(query_embeddings=[embedding.tolist()], n_results=n, include=["distances"])
        return [(cid, 1.0 - dist) for cid, dist in zip(res["ids"][0], res["distances"][0])]
