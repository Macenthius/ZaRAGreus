"""Ingest -> chunk -> embed -> index into Chroma. Idempotent: the collection is rebuilt.

Usage:  python scripts/build_index.py
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from rag.chunking import chunk_documents, chunk_stats  # noqa: E402
from rag.embeddings import Embedder  # noqa: E402
from rag.ingest import corpus_stats, load_documents  # noqa: E402
from rag.store import VectorStore  # noqa: E402

log = logging.getLogger("build_index")


def write_json(name: str, data: dict) -> None:
    config.RESULTS_DIR.mkdir(exist_ok=True)
    (config.RESULTS_DIR / name).write_text(json.dumps(data, indent=2), encoding="utf-8")
    log.info("%s: %s", name, data)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    t0 = time.perf_counter()
    docs = load_documents()
    write_json("corpus_stats.json", corpus_stats(docs))

    chunks = chunk_documents(docs)
    write_json("chunk_stats.json", chunk_stats(chunks))

    embedder = Embedder()
    t_embed = time.perf_counter()
    vectors = embedder.embed_passages([c.text for c in chunks])
    embed_s = time.perf_counter() - t_embed

    store = VectorStore()
    store.reset()
    store.add(chunks, vectors)
    write_json("index_stats.json", {
        "embedding_model": config.EMBED_MODEL,
        "embedding_dim": int(vectors.shape[1]),
        "chunk_count": store.count(),
        "embedding_time_s": round(embed_s, 1),
        "total_build_time_s": round(time.perf_counter() - t0, 1),
        "vector_store": "chromadb PersistentClient (cosine)",
    })


if __name__ == "__main__":
    main()
