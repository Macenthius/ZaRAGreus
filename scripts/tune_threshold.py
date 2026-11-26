"""Sweep the relevance-gate threshold on eval/questions.json (best dense cosine per question).

For each threshold t: a question is refused if best_dense < t.
  false-refusal rate  = answerable questions refused / 30
  correct-refusal rate = unanswerable questions refused / 10
We pick the threshold maximising (correct refusals - false refusals), breaking ties toward
the LOWER threshold (fewer false refusals). NOTE: tuned on the same set we evaluate on.

Usage:  python scripts/tune_threshold.py
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from rag.embeddings import Embedder  # noqa: E402
from rag.retrieval import Retriever  # noqa: E402
from rag.store import VectorStore  # noqa: E402

log = logging.getLogger("tune_threshold")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    questions = json.loads(config.EVAL_PATH.read_text(encoding="utf-8"))
    retriever = Retriever(VectorStore(), Embedder())
    scores = []
    for q in questions:
        best = retriever.dense(q["question"], 1)[0][1]
        scores.append({"id": q["id"], "answerable": q["answerable"], "best_dense": round(best, 4)})

    ans = [s["best_dense"] for s in scores if s["answerable"]]
    una = [s["best_dense"] for s in scores if not s["answerable"]]
    sweep = []
    for i in range(50, 86):
        t = i / 100
        fr = sum(s < t for s in ans) / len(ans)
        cr = sum(s < t for s in una) / len(una)
        sweep.append({"threshold": t, "false_refusal_rate": round(fr, 3), "correct_refusal_rate": round(cr, 3),
                      "objective": round(cr - fr, 3)})
    best = max(sweep, key=lambda r: (r["objective"], -r["threshold"]))
    out = {
        "chosen_threshold": best["threshold"],
        "rule": "maximise correct_refusal_rate - false_refusal_rate; ties -> lower threshold",
        "caveat": "Tuned on the same 40 evaluation questions that are later used for evaluation.",
        "answerable_best_dense": {"min": min(ans), "max": max(ans), "mean": round(sum(ans) / len(ans), 4)},
        "unanswerable_best_dense": {"min": min(una), "max": max(una), "mean": round(sum(una) / len(una), 4)},
        "per_question": scores,
        "sweep": sweep,
    }
    config.RESULTS_DIR.mkdir(exist_ok=True)
    (config.RESULTS_DIR / "threshold_tuning.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot([r["threshold"] for r in sweep], [r["correct_refusal_rate"] for r in sweep], label="correct-refusal rate (unanswerable)")
    ax.plot([r["threshold"] for r in sweep], [r["false_refusal_rate"] for r in sweep], label="false-refusal rate (answerable)")
    ax.axvline(best["threshold"], color="grey", ls="--", label=f"chosen = {best['threshold']:.2f}")
    ax.set_xlabel("relevance threshold (best dense cosine)")
    ax.set_ylabel("rate")
    ax.set_title("Relevance-gate threshold sweep (40 eval questions)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(config.RESULTS_DIR / "threshold_sweep.png", dpi=120)
    log.info("Answerable best-dense: %s | Unanswerable: %s", out["answerable_best_dense"], out["unanswerable_best_dense"])
    log.info("Chosen threshold %.2f: %s", best["threshold"], best)


if __name__ == "__main__":
    main()
