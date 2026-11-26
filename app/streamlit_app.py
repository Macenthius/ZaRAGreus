"""Streamlit UI for the Rust Book Q&A assistant.

Run:  streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from rag.llm import OllamaClient  # noqa: E402
from rag.pipeline import RAGPipeline  # noqa: E402

EXAMPLES = [
    "What are the three rules of ownership?",
    "How does RefCell<T> enforce the borrowing rules?",
    "What does the ? operator do?",
    "How do I share a Mutex between multiple threads?",
    "What are the lifetime elision rules?",
]

st.set_page_config(page_title="Rust Book Q&A", page_icon="🦀", layout="wide")


@st.cache_resource(show_spinner="Loading embedding model and index ...")
def get_pipeline() -> RAGPipeline:
    return RAGPipeline.from_disk()


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("Settings")
    mode = st.radio("Retrieval mode", ["hybrid", "dense", "bm25"], index=0,
                    help="hybrid = dense top-20 + BM25 top-20 fused with Reciprocal Rank Fusion")
    top_k = st.slider("top_k (passages sent to the LLM)", 1, 8, config.TOP_K)
    model = st.text_input("Ollama model", config.LLM_MODEL)
    show_latency = st.toggle("Show latency", value=True)
    client = OllamaClient(model=model)
    if not client.is_available():
        st.error(f"Ollama is not reachable at {config.OLLAMA_URL}. Answers will use the extractive fallback.")
    elif not client.has_model(model):
        st.warning(f"Model `{model}` is not pulled. Run `ollama pull {model}`.")
    else:
        st.success(f"Ollama OK - `{model}`")
    st.caption(f"Relevance gate: refuse if best dense similarity < {config.RELEVANCE_THRESHOLD:.2f}")

# ------------------------------------------------------------------ main
st.title("🦀 Rust Book Q&A")
st.write("Answers grounded in *The Rust Programming Language* book, with sources. "
         "Questions the book does not cover are refused.")

cols = st.columns(len(EXAMPLES))
for col, ex in zip(cols, EXAMPLES):
    if col.button(ex, use_container_width=True):
        st.session_state["question"] = ex

question = st.text_input("Your question", key="question", placeholder="e.g. What is a string slice?")

if question:
    pipeline = get_pipeline()
    answer, stream = pipeline.ask_stream(question, mode=mode, top_k=top_k, model=model)
    st.subheader("Answer")
    if answer.refused:
        st.warning(f"{config.REFUSAL_TEXT}\n\nBest match similarity was **{answer.best_dense:.3f}**, "
                   f"below the relevance threshold of {config.RELEVANCE_THRESHOLD:.2f}, so the LLM was not called.")
    else:
        full = st.write_stream(stream)
        if answer.used_fallback:
            st.error(answer.warning or "LLM unavailable - extractive fallback shown.")
        elif isinstance(full, str) and config.REFUSAL_TEXT.rstrip(".") in full:
            st.info("The model judged that the retrieved passages do not answer this question.")

    if show_latency:
        st.caption(f"Retrieve: {answer.latency['retrieve_ms']:.0f} ms | "
                   f"Generate: {answer.latency['generate_ms']:.0f} ms | mode: {mode} | best dense: {answer.best_dense:.3f}")

    st.subheader("Sources")
    for i, h in enumerate(answer.sources, 1):
        m = h.metadata
        scores = []
        if h.dense_score is not None:
            scores.append(f"dense {h.dense_score:.3f}")
        if h.bm25_score is not None:
            scores.append(f"bm25 {h.bm25_score:.2f}")
        if h.fused_score is not None:
            scores.append(f"rrf {h.fused_score:.4f}")
        st.markdown(f"**[{i}] {m['chapter_title']}** - {m['heading_path']}  \n"
                    f"{' | '.join(scores) or 'no scores'} | [read online]({m['url']})")
        with st.expander(f"Chunk text ({m['n_words']} words, `{h.chunk_id}`)"):
            st.markdown(h.text)
