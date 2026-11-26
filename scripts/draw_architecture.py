"""Draw docs/architecture.png with matplotlib (no graphviz needed).

Usage:  python scripts/draw_architecture.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

W, H = 2.3, 0.9  # box size


def box(ax, x, y, text, color):
    ax.add_patch(FancyBboxPatch((x - W / 2, y - H / 2), W, H, boxstyle="round,pad=0.05",
                                fc=color, ec="#333333", lw=1))
    ax.text(x, y, text, ha="center", va="center", fontsize=8.5)


def arrow(ax, p, q, label=""):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=12, color="#333333", lw=1))
    if label:
        ax.text((p[0] + q[0]) / 2, (p[1] + q[1]) / 2 + 0.12, label, fontsize=7, ha="center", color="#555555")


def main() -> None:
    fig, ax = plt.subplots(figsize=(16, 7))
    ax.set_xlim(0, 17)
    ax.set_ylim(0, 7.4)
    ax.axis("off")
    ing, qry, gate, llm = "#DCEBF7", "#E3F2DC", "#FCE8CF", "#EADCF2"

    ax.text(0.2, 7.0, "Ingestion pipeline (offline)", fontsize=12, weight="bold")
    xs = [1.5, 4.3, 7.1, 9.9, 12.7]
    labels = ["rust-lang/book\n(GitHub, shallow clone)", "ingest.py\nresolve includes,\nstrip HTML, metadata",
              "chunking.py\nheader-aware, ~350 tok,\n15% overlap, code intact",
              "embeddings.py\nfastembed\nbge-small-en-v1.5 (384-d)", "Chroma\nchroma_db/ (cosine)"]
    for x, t in zip(xs, labels):
        box(ax, x, 6.0, t, ing)
    for a, b in zip(xs, xs[1:]):
        arrow(ax, (a + W / 2, 6.0), (b - W / 2, 6.0))

    ax.text(0.2, 4.6, "Query pipeline (online)", fontsize=12, weight="bold")
    box(ax, 1.5, 3.0, "User question\n(Streamlit UI)", qry)
    box(ax, 4.3, 3.9, "Dense top-20\nbge query prefix", qry)
    box(ax, 4.3, 2.1, "BM25 top-20\ncode-aware tokenizer", qry)
    box(ax, 7.1, 3.0, "Reciprocal Rank Fusion\nk=60 -> top_k=4", qry)
    box(ax, 7.1, 0.8, "Relevance gate\nbest cosine >= 0.70 ?", gate)
    box(ax, 9.9, 3.0, "Prompt builder\nnumbered context,\ncite [n], refuse rule", llm)
    box(ax, 12.7, 3.0, "Ollama /api/chat\nqwen2.5:0.5b\ntemp 0.1, ctx 4096", llm)
    box(ax, 12.7, 0.8, "Refusal or extractive\nfallback (Ollama down)", gate)
    box(ax, 15.5, 3.0, "Answer + citations\n+ sources panel", qry)

    arrow(ax, (1.5 + W / 2, 3.2), (4.3 - W / 2, 3.9))
    arrow(ax, (1.5 + W / 2, 2.8), (4.3 - W / 2, 2.1))
    arrow(ax, (4.3 + W / 2, 3.9), (7.1 - W / 2, 3.2))
    arrow(ax, (4.3 + W / 2, 2.1), (7.1 - W / 2, 2.8))
    arrow(ax, (4.3, 3.9 - H / 2), (7.1 - W / 2, 0.9), "best score")
    arrow(ax, (12.7, 6.0 - H / 2), (4.3 + 0.4, 3.9 + H / 2), "vectors / chunks")
    arrow(ax, (7.1 + W / 2, 3.0), (9.9 - W / 2, 3.0), "pass")
    arrow(ax, (9.9 + W / 2, 3.0), (12.7 - W / 2, 3.0))
    arrow(ax, (12.7 + W / 2, 3.0), (15.5 - W / 2, 3.0), "stream")
    arrow(ax, (7.1 + W / 2, 0.8), (12.7 - W / 2, 0.8), "fail -> refuse")
    arrow(ax, (12.7 + W / 2, 0.9), (15.5 - 0.3, 3.0 - H / 2))

    ax.set_title("Rust Book RAG - architecture", fontsize=14)
    fig.tight_layout()
    out = config.ROOT / "docs" / "architecture.png"
    fig.savefig(out, dpi=130)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
