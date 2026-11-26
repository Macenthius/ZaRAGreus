"""Dense, BM25 and hybrid (Reciprocal Rank Fusion) retrieval plus a relevance gate."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import numpy as np
from rank_bm25 import BM25Okapi

import config
from rag.chunking import Chunk
from rag.embeddings import Embedder
from rag.store import VectorStore

log = logging.getLogger(__name__)

# Keeps Rust-ish identifiers intact: Vec<T>, &mut, Rc<RefCell<T>>, Box<dyn, std::fmt, Option<T>, ?
TOKEN_RE = re.compile(r"&mut|&'?\w+|[a-z_][a-z0-9_]*(?:::[a-z_][a-z0-9_]*)*(?:<[^<>\s]*(?:<[^<>\s]*>)?[^<>\s]*>)?|\d+|[?!]")
STOPWORDS = set("""a an the is are was were be been of to in on for and or with as by at from it its this that
these those how what why when which who do does did can i you we they he she my your our their not no
use using used into about than then so if else there here have has had will would should could""".split())


def tokenize(text: str) -> list[str]:
    """Lowercase tokenizer for BM25 that keeps code identifiers like vec<t>, &mut, std::rc.

    Generic forms such as `vec<t>` also emit their base name (`vec`) so a query for
    "Vec" still matches.
    """
    toks: list[str] = []
    for t in TOKEN_RE.findall(text.lower()):
        if t in STOPWORDS:
            continue
        toks.append(t)
        if "<" in t:
            toks.append(t.split("<", 1)[0])
        if "::" in t:
            toks.extend(p for p in t.split("::") if p and "<" not in p)
    return toks


@dataclass
class Hit:
    """One retrieved chunk and all its scores."""
    chunk_id: str
    text: str
    metadata: dict
    dense_score: float | None = None
    bm25_score: float | None = None
    fused_score: float | None = None
    rank: int = 0
    extra: dict = field(default_factory=dict)


def rrf_fuse(rankings: list[list[str]], k: int = config.RRF_K) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion: score(d) = sum over rankings of 1 / (k + rank), rank from 1."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


@dataclass
class RetrievalResult:
    hits: list[Hit]
    best_dense: float          # best dense cosine similarity for the query (gate input)
    passed_gate: bool


class Retriever:
    """Holds the dense index (Chroma) and an in-memory BM25 index over the same chunks."""

    def __init__(self, store: VectorStore, embedder: Embedder) -> None:
        self.store = store
        self.embedder = embedder
        self.chunks = {c.chunk_id: c for c in store.all_chunks()}
        if not self.chunks:
            raise RuntimeError("Vector store is empty - run `python scripts/build_index.py` first.")
        self._ids = list(self.chunks)
        self.bm25 = BM25Okapi([tokenize(self.chunks[i].text) for i in self._ids])
        log.info("Retriever ready: %d chunks", len(self._ids))

    # -- individual retrievers ------------------------------------------------
    def dense(self, query: str, n: int) -> list[tuple[str, float]]:
        return self.store.query(self.embedder.embed_query(query), n)

    def bm25_search(self, query: str, n: int) -> list[tuple[str, float]]:
        scores = self.bm25.get_scores(tokenize(query))
        order = np.argsort(-scores)[:n]
        return [(self._ids[i], float(scores[i])) for i in order if scores[i] > 0]

    # -- main entry -----------------------------------------------------------
    def retrieve(self, query: str, mode: str = config.RETRIEVAL_MODE, top_k: int = config.TOP_K,
                 threshold: float = config.RELEVANCE_THRESHOLD) -> RetrievalResult:
        """Retrieve top_k hits with the chosen mode and apply the dense relevance gate."""
        n = max(config.CANDIDATES_PER_RETRIEVER, top_k)
        dense = self.dense(query, n)            # always computed: needed for the gate
        dense_map = dict(dense)
        best_dense = dense[0][1] if dense else 0.0
        bm25 = self.bm25_search(query, n) if mode in ("bm25", "hybrid") else []
        bm25_map = dict(bm25)

        if mode == "dense":
            ranked = [(cid, s) for cid, s in dense]
        elif mode == "bm25":
            ranked = bm25
        elif mode == "hybrid":
            ranked = rrf_fuse([[c for c, _ in dense], [c for c, _ in bm25]])
        else:
            raise ValueError(f"Unknown retrieval mode: {mode}")

        hits = []
        for rank, (cid, score) in enumerate(ranked[:top_k], start=1):
            ch = self.chunks[cid]
            hits.append(Hit(
                chunk_id=cid, text=ch.text, metadata=ch.metadata,
                dense_score=dense_map.get(cid),
                bm25_score=bm25_map.get(cid),
                fused_score=score if mode == "hybrid" else None,
                rank=rank,
            ))
        return RetrievalResult(hits, best_dense, passed_gate=best_dense >= threshold)
