"""Compare chunk-size targets (200 / 350 / 500 tokens) on hybrid retrieval Hit@3 and MRR@10.

Each setting is chunked, embedded and indexed into a temporary Chroma directory, then evaluated
on the 30 answerable questions exactly as in scripts/evaluate.py.

Usage:  python scripts/chunk_ablation.py
"""
from __future__ import annotations

import json
import logging
import shutil
import statistics as st
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from rag.chunking import chunk_documents  # noqa: E402
from rag.embeddings import Embedder  # noqa: E402
from rag.ingest import load_documents  # noqa: E402
from rag.retrieval import Retriever  # noqa: E402
from rag.store import VectorStore  # noqa: E402

log = logging.getLogger("chunk_ablation")
TARGETS = [200, 350, 500]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    questions = [q for q in json.loads(config.EVAL_PATH.read_text(encoding="utf-8")) if q["answerable"]]
    docs = load_documents()
    embedder = Embedder()
    results = []
    for target in TARGETS:
        t0 = time.perf_counter()
        chunks = chunk_documents(docs, target_tokens=target)
        tmp = Path(tempfile.mkdtemp(prefix=f"ablation_{target}_"))
        store = VectorStore(path=tmp, name=f"ablation_{target}")
        store.reset()
        store.add(chunks, embedder.embed_passages([c.text for c in chunks]))
        retriever = Retriever(store, embedder)
        row = {"target_tokens": target, "chunks": len(chunks),
               "mean_words": round(st.mean(c.metadata["n_words"] for c in chunks), 1)}
        for mode in ("hybrid", "dense"):
            hit3, rr = 0, []
            for q in questions:
                files = [h.metadata["file"] for h in retriever.retrieve(q["question"], mode=mode, top_k=10, threshold=0).hits]
                first = next((i + 1 for i, f in enumerate(files) if f in q["gold_files"]), None)
                hit3 += first is not None and first <= 3
                rr.append(1 / first if first else 0.0)
            row[f"{mode}_hit@3"] = round(hit3 / len(questions), 3)
            row[f"{mode}_mrr@10"] = round(st.mean(rr), 3)
        row["build_and_eval_s"] = round(time.perf_counter() - t0, 1)
        results.append(row)
        log.info("%s", row)
        del retriever, store
        shutil.rmtree(tmp, ignore_errors=True)
    out = {"note": "Same 30 answerable questions as evaluate.py; gold = chunk from a gold chapter file.",
           "results": results}
    (config.RESULTS_DIR / "chunk_ablation.json").write_text(json.dumps(out, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
