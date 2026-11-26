# Rust Book RAG: a source-grounded Q&A assistant for *The Rust Programming Language*

A Retrieval-Augmented Generation (RAG) application that answers questions about Rust using only passages
retrieved from *The Rust Programming Language* book. Every answer cites its sources, links to the online
book, and the assistant refuses when the book does not cover the question.

**Target users:** students and developers learning Rust who want quick answers they can check against the book.

![architecture](docs/architecture.png)

## Features
- **Corpus:** the official Rust Book source (`rust-lang/book`, MIT / Apache-2.0), with mdBook `{{#include}}`
  directives resolved so code listings are part of the text.
- **Header-aware chunking:** chunks follow the book's headings, carry their heading path
  (e.g. `Understanding Ownership > References and Borrowing`), target ~350 tokens with ~15% overlap,
  and never split a code block.
- **Three retrieval modes:** dense (bge-small + Chroma), BM25 with a Rust-aware tokenizer, and hybrid
  (Reciprocal Rank Fusion).
- **Relevance gate:** low-similarity questions are refused before the LLM is called.
- **Grounded generation:** a local LLM through Ollama (`qwen2.5:0.5b` by default) answers only from numbered
  context and cites `[1]`, `[2]`, ...
- **Graceful degradation:** if Ollama is down, a clearly labelled extractive answer (the best passage) is shown.
- **Streamlit UI:** streamed answers, sources panel with scores and links, mode / top_k / model controls,
  latency display, Ollama status, and example questions.
- **Evaluation:** a 40-question hand-checked test set, retrieval metrics for all modes, end-to-end answer metrics,
  threshold tuning, and a chunk-size ablation.

## Architecture summary
See [docs/architecture.md](docs/architecture.md) for the Mermaid diagram and the step-by-step workflow.

1. **Offline:** fetch the book, then clean, chunk, embed and store the chunks in Chroma.
2. **Online:** embed the question, retrieve with dense + BM25, fuse with RRF, apply the relevance gate,
   build a grounded prompt, generate with Ollama, and show the answer with its sources.

## Tech stack
| Component | Choice |
|---|---|
| Language | Python 3.11+ (developed on 3.12.10) |
| Embeddings | `fastembed` with `BAAI/bge-small-en-v1.5` (ONNX, 384-d, no torch) |
| Vector DB | `chromadb` PersistentClient, cosine space |
| Sparse retrieval | `rank_bm25` (BM25Okapi) |
| Fusion | Reciprocal Rank Fusion, k = 60 |
| LLM | Ollama, `qwen2.5:0.5b` (configurable, e.g. `qwen2.5:1.5b`), via HTTP `/api/chat` |
| UI | Streamlit |
| Tests | pytest |

## Setup

### 1. Install Ollama and pull the model
Download Ollama from https://ollama.com/download, install it, then:
```
ollama pull qwen2.5:0.5b
# optional, for the comparison run
ollama pull qwen2.5:1.5b
```
Ollama runs a local server at `http://localhost:11434` (override with the `OLLAMA_URL` environment variable).

### 2. Python environment

**Windows PowerShell**
```powershell
cd rust-book-rag
py -3.12 -m venv .venv          # or: python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**bash (Linux / macOS / Git Bash)**
```bash
cd rust-book-rag
python3 -m venv .venv
source .venv/bin/activate        # Git Bash on Windows: source .venv/Scripts/activate
pip install -r requirements.txt
```

### 3. Build the knowledge base (same commands in both shells)
```
python scripts/fetch_corpus.py      # optional: data/raw is already committed
python scripts/build_index.py       # ~3-4 min on CPU; first run downloads the embedding model
```

### 4. Run the app
```
streamlit run app/streamlit_app.py
```
Open http://localhost:8501.

### 5. Evaluate
```
python scripts/tune_threshold.py                 # relevance-gate sweep
python scripts/evaluate.py                       # retrieval + answers with qwen2.5:0.5b
python scripts/evaluate.py --model qwen2.5:1.5b  # second model, separate result files
python scripts/evaluate.py --retrieval-only      # no LLM needed
python scripts/chunk_ablation.py                 # 200 / 350 / 500-token chunks (~10 min)
```

### 6. Tests
```
python -m pytest -v
```

## Repository structure
```
rust-book-rag/
  config.py                 all tunables (chunk size, overlap, top_k, threshold, model names)
  data/raw/                 Rust Book markdown + included listings (unmodified copies)
  data/corpus_manifest.json repo URL, commit SHA, file and word counts, fetch date
  rag/ingest.py             load + clean markdown, resolve includes, metadata
  rag/chunking.py           header-aware chunker
  rag/embeddings.py         fastembed wrapper
  rag/store.py              Chroma wrapper
  rag/retrieval.py          dense, BM25, hybrid (RRF), relevance gate
  rag/llm.py                Ollama client, prompt builder, extractive fallback
  rag/pipeline.py           RAGPipeline.ask() -> Answer
  scripts/                  fetch_corpus, build_index, tune_threshold, evaluate, chunk_ablation, draw_architecture
  app/streamlit_app.py      UI
  eval/questions.json       40-question test set (30 answerable, 10 unanswerable)
  results/                  all generated metrics, charts and sample outputs
  docs/                     architecture.md, architecture.png, DEV_LOG.md
  tests/                    pytest suite
```

## Example questions
- What are the three rules of ownership?
- How does RefCell<T> enforce the borrowing rules?
- What does the ? operator do?
- How do I share a Mutex between multiple threads?
- What are the lifetime elision rules?
- *Refused:* What is the capital of France?

## Results
All numbers come from real runs on the development machine (Windows 11, CPU only); the raw files are in `results/`.

**Corpus and index:** 111 pages (21 chapters + 8 appendix pages), 201,287 words after inlining code listings,
950 code blocks -> **1,096 chunks** (mean 196 words, 64% contain code), 384-d embeddings, 197 s build.

**Retrieval** (30 answerable questions; a hit is a chunk from a gold chapter file):

| mode | Hit@1 | Hit@3 | Hit@5 | MRR@10 |
|---|---|---|---|---|
| dense | 0.967 | 1.000 | 1.000 | 0.983 |
| bm25 | 0.600 | 0.867 | 0.933 | 0.737 |
| hybrid (RRF, default) | 0.800 | 0.933 | 0.967 | 0.879 |

Dense retrieval alone performed best on this set; RRF gives the weaker BM25 ranking equal weight. See
`docs/DEV_LOG.md` for the analysis.

**Relevance gate:** threshold 0.70 gives 0% false refusals and 90% correct refusals on the test set
*before* the LLM is involved (tuned on the same set, see `results/threshold_tuning.json`).

**Chunk-size ablation** (`results/chunk_ablation.json`, same 30 questions):

| target tokens | chunks | hybrid Hit@3 | hybrid MRR@10 | dense Hit@3 | dense MRR@10 |
|---|---|---|---|---|---|
| 200 | 1,842 | 0.967 | 0.881 | 1.000 | 0.967 |
| **350 (chosen)** | 1,096 | 0.933 | 0.879 | 1.000 | 0.983 |
| 500 | 817 | 0.933 | 0.852 | 0.933 | 0.893 |

350 tokens gives the best dense MRR and near-best hybrid MRR. It also keeps 4 retrieved chunks
(~1,100 tokens) well inside the 4,096-token context of the small LLM. 500-token chunks clearly hurt.

**End-to-end answers:** *not yet run.* Ollama was not installed on the development machine when this
README was written, so there are no LLM answer metrics yet. Run `python scripts/evaluate.py` after
installing Ollama to produce `results/answer_metrics_qwen2.5-0.5b.json`, `results/sample_outputs.md`
and `results/manual_review.csv`.

<!-- ANSWER_RESULTS -->

## Limitations
- The test set is small (40 questions) and was written by the developer; the threshold was tuned on it.
- Key-fact coverage is a lexical proxy for correctness; `results/manual_review.csv` is for human judgement.
- `qwen2.5:0.5b` is very small: it can paraphrase loosely, miss citations, or miss refusals.
- Plain RRF underperforms dense-only here; weights are not tuned.
- Token counts are estimated from word counts (x1.3), not from a real tokenizer.
- Single book only; no conversation memory.

## Future work
- Weighted RRF or a cross-encoder reranker (e.g. bge-reranker) on the fused candidates.
- A larger, independently written test set, and LLM-as-judge or human grading at scale.
- Multi-turn chat with question rewriting.
- Add the Rust Reference and standard-library docs as extra corpora.

## Credits and licence
- *The Rust Programming Language* by Steve Klabnik, Carol Nichols and Chris Krycho, with contributions from the
  Rust Community, MIT OR Apache-2.0. See [NOTICE.md](NOTICE.md).
- Embedding model: BAAI bge-small-en-v1.5 (MIT). LLM: Qwen2.5 (Apache-2.0) served by Ollama.
