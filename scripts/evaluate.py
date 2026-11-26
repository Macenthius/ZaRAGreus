"""Evaluate retrieval (dense / bm25 / hybrid) and end-to-end answers.

Usage:
  python scripts/evaluate.py                       # retrieval + answers with config.LLM_MODEL
  python scripts/evaluate.py --model qwen2.5:1.5b  # answers with another Ollama model
  python scripts/evaluate.py --retrieval-only      # skip the LLM part
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from rag.embeddings import Embedder  # noqa: E402
from rag.llm import OllamaClient, prompt_template_text  # noqa: E402
from rag.pipeline import RAGPipeline  # noqa: E402
from rag.retrieval import Retriever  # noqa: E402
from rag.store import VectorStore  # noqa: E402

log = logging.getLogger("evaluate")
MODES = ["dense", "bm25", "hybrid"]
EVAL_DEPTH = 10  # ranks considered for MRR


def norm(text: str) -> str:
    return " ".join(text.lower().replace("’", "'").split())


# ------------------------------------------------------------------ retrieval
def retrieval_metrics(retriever: Retriever, questions: list[dict]) -> dict:
    """Hit@1/3/5 and MRR@10 per mode. A hit = retrieved chunk from a gold file."""
    out = {}
    for mode in MODES:
        h1 = h3 = h5 = 0
        rr = []
        per_q = []
        for q in questions:
            res = retriever.retrieve(q["question"], mode=mode, top_k=EVAL_DEPTH, threshold=0.0)
            files = [h.metadata["file"] for h in res.hits]
            first = next((i + 1 for i, f in enumerate(files) if f in q["gold_files"]), None)
            h1 += first is not None and first <= 1
            h3 += first is not None and first <= 3
            h5 += first is not None and first <= 5
            rr.append(1 / first if first else 0.0)
            per_q.append({"id": q["id"], "first_gold_rank": first, "top5_files": files[:5]})
        n = len(questions)
        out[mode] = {"hit@1": round(h1 / n, 3), "hit@3": round(h3 / n, 3), "hit@5": round(h5 / n, 3),
                     "mrr@10": round(st.mean(rr), 3), "n": n, "per_question": per_q}
    return out


def plot_retrieval(metrics: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = ["hit@1", "hit@3", "hit@5", "mrr@10"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    w = 0.26
    colors = {"dense": "#4C78A8", "bm25": "#F58518", "hybrid": "#54A24B"}
    for i, mode in enumerate(MODES):
        vals = [metrics[mode][m] for m in names]
        xs = [j + (i - 1) * w for j in range(len(names))]
        bars = ax.bar(xs, vals, w, label=mode, color=colors[mode])
        ax.bar_label(bars, fmt="%.2f", fontsize=8)
    ax.set_xticks(range(len(names)), names)
    ax.set_ylim(0, 1.25)
    ax.set_ylabel("score")
    ax.set_title(f"Retrieval comparison on {metrics['dense']['n']} answerable questions")
    ax.legend(loc="upper center", ncol=3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)


# ------------------------------------------------------------------ answers
def answer_eval(pipeline: RAGPipeline, questions: list[dict], model: str) -> tuple[dict, list[dict]]:
    """Run the full pipeline on every question and compute answer metrics."""
    records = []
    for i, q in enumerate(questions, 1):
        a = pipeline.ask(q["question"], mode="hybrid", top_k=config.TOP_K, model=model)
        text = norm(a.answer)
        found = [k for k in q["key_facts"] if norm(k) in text]
        rec = {
            "id": q["id"], "question": q["question"], "answerable": q["answerable"],
            "answer": a.answer, "refused": a.refused, "gate_refused": a.refused and a.latency["generate_ms"] == 0,
            "used_fallback": a.used_fallback, "best_dense": round(a.best_dense, 4),
            "key_facts": q["key_facts"], "key_facts_found": found,
            "key_fact_coverage": round(len(found) / len(q["key_facts"]), 3) if q["key_facts"] else None,
            "has_citation": bool(__import__("re").search(r"\[\d+\]", a.answer)),
            "gold_files": q["gold_files"],
            "retrieved": [{"chunk_id": h.chunk_id, "file": h.metadata["file"], "heading_path": h.metadata["heading_path"],
                           "dense": None if h.dense_score is None else round(h.dense_score, 4),
                           "bm25": None if h.bm25_score is None else round(h.bm25_score, 3),
                           "fused": None if h.fused_score is None else round(h.fused_score, 5)} for h in a.sources],
            "retrieve_ms": round(a.latency["retrieve_ms"], 1), "generate_ms": round(a.latency["generate_ms"], 1),
        }
        records.append(rec)
        log.info("[%d/%d] %s refused=%s cov=%s %.0fms", i, len(questions), q["id"], a.refused,
                 rec["key_fact_coverage"], a.latency["generate_ms"])

    ans = [r for r in records if r["answerable"]]
    una = [r for r in records if not r["answerable"]]
    generated = [r for r in records if not r["gate_refused"]]
    metrics = {
        "model": model, "retrieval_mode": "hybrid", "top_k": config.TOP_K,
        "relevance_threshold": config.RELEVANCE_THRESHOLD,
        "n_answerable": len(ans), "n_unanswerable": len(una),
        "key_fact_coverage_mean": round(st.mean(r["key_fact_coverage"] for r in ans), 3),
        "key_fact_coverage_mean_non_refused": round(st.mean([r["key_fact_coverage"] for r in ans if not r["refused"]] or [0]), 3),
        "citation_rate_answerable_non_refused": round(st.mean([r["has_citation"] for r in ans if not r["refused"]] or [0]), 3),
        "correct_refusal_rate": round(sum(r["refused"] for r in una) / len(una), 3),
        "correct_refusals_by_gate": sum(r["gate_refused"] for r in una),
        "correct_refusals_by_llm": sum(r["refused"] and not r["gate_refused"] for r in una),
        "false_refusal_rate": round(sum(r["refused"] for r in ans) / len(ans), 3),
        "fallback_used": sum(r["used_fallback"] for r in records),
        "mean_retrieve_ms": round(st.mean(r["retrieve_ms"] for r in records), 1),
        "mean_generate_ms_when_generated": round(st.mean([r["generate_ms"] for r in generated] or [0]), 1),
        "median_generate_ms_when_generated": round(st.median([r["generate_ms"] for r in generated] or [0]), 1),
    }
    return metrics, records


def write_samples(records: list[dict], path: Path, model: str) -> None:
    """Pick representative examples: best, worst, refusals, failures."""
    ans = [r for r in records if r["answerable"]]
    una = [r for r in records if not r["answerable"]]
    good = sorted([r for r in ans if not r["refused"]], key=lambda r: -r["key_fact_coverage"])[:4]
    weak = sorted([r for r in ans if r not in good], key=lambda r: r["key_fact_coverage"])[:2]
    refusals = [r for r in una if r["refused"]][:2]
    missed = [r for r in una if not r["refused"]][:1]
    false_ref = [r for r in ans if r["refused"]][:1]
    picked, seen = [], set()
    for label, group in [("Good answer", good), ("Weak / failure case", weak), ("Correct refusal", refusals),
                         ("Missed refusal (failure)", missed), ("False refusal (failure)", false_ref)]:
        for r in group:
            if r["id"] not in seen:
                seen.add(r["id"])
                picked.append((label, r))
    lines = [f"# Sample outputs ({model}, hybrid retrieval, top_k={config.TOP_K})", "",
             "Generated automatically by `scripts/evaluate.py` from a real run. Examples are chosen by rule: "
             "highest key-fact coverage, lowest coverage, refusals, and any refusal failures.", ""]
    for label, r in picked:
        lines += [f"## {r['id']} - {label}", "", f"**Question:** {r['question']}", "",
                  f"**Best dense similarity:** {r['best_dense']}  |  **Refused:** {r['refused']}  |  "
                  f"**Key facts found:** {r['key_facts_found']} of {r['key_facts']}  |  "
                  f"**Latency:** retrieve {r['retrieve_ms']} ms, generate {r['generate_ms']} ms", "",
                  "**Answer:**", "", *["> " + ln for ln in r["answer"].splitlines()], "", "**Retrieved sources:**", ""]
        for i, h in enumerate(r["retrieved"], 1):
            lines.append(f"{i}. `{h['chunk_id']}` - {h['heading_path']} (dense={h['dense']}, bm25={h['bm25']}, fused={h['fused']})")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_manual_review(records: list[dict], path: Path) -> None:
    rng = random.Random(42)
    sample = rng.sample([r for r in records if r["answerable"]], 12)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "question", "answer", "sources", "correct (0/0.5/1)", "grounded (0/1)", "notes"])
        for r in sorted(sample, key=lambda r: r["id"]):
            w.writerow([r["id"], r["question"], r["answer"], "; ".join(h["chunk_id"] for h in r["retrieved"]), "", "", ""])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default=config.LLM_MODEL)
    ap.add_argument("--retrieval-only", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    res_dir = config.RESULTS_DIR
    res_dir.mkdir(exist_ok=True)
    questions = json.loads(config.EVAL_PATH.read_text(encoding="utf-8"))
    answerable = [q for q in questions if q["answerable"]]
    retriever = Retriever(VectorStore(), Embedder())

    rm = retrieval_metrics(retriever, answerable)
    (res_dir / "retrieval_metrics.json").write_text(json.dumps(rm, indent=2), encoding="utf-8")
    plot_retrieval(rm, res_dir / "retrieval_comparison.png")
    for mode in MODES:
        log.info("%-6s %s", mode, {k: v for k, v in rm[mode].items() if k != "per_question"})
    (res_dir / "prompt_template.txt").write_text(prompt_template_text(), encoding="utf-8")

    if args.retrieval_only:
        return
    client = OllamaClient(model=args.model)
    if not client.is_available():
        log.error("Ollama is not reachable at %s - answer evaluation skipped.", config.OLLAMA_URL)
        sys.exit(2)
    if not client.has_model(args.model):
        log.error("Model %s is not pulled. Run: ollama pull %s", args.model, args.model)
        sys.exit(2)
    tag = args.model.replace(":", "-")
    metrics, records = answer_eval(RAGPipeline(retriever, client), questions, args.model)
    (res_dir / f"answers_{tag}.json").write_text(json.dumps({"metrics": metrics, "records": records}, indent=2), encoding="utf-8")
    (res_dir / f"answer_metrics_{tag}.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    write_samples(records, res_dir / ("sample_outputs.md" if args.model == config.LLM_MODEL else f"sample_outputs_{tag}.md"), args.model)
    if args.model == config.LLM_MODEL:
        write_manual_review(records, res_dir / "manual_review.csv")
    log.info("Answer metrics: %s", metrics)


if __name__ == "__main__":
    main()
