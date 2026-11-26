# Development log

All numbers below come from real runs on the development machine (Windows 11, Python 3.12.10, CPU only),
on 2026-11-26.

## Phase 0: environment
- Created `.venv` and installed pinned dependencies (`requirements.txt`). Python 3.12.10 was available
  (the brief requires 3.11+).
- **Ollama was not installed** on the machine. An automatic install with `winget` was attempted but was
  blocked by the environment's permission policy, so Ollama must be installed manually from
  https://ollama.com/download. Everything that does not need the LLM was built and run in the meantime.

## Phase 1: knowledge base
- `scripts/fetch_corpus.py` shallow-clones `rust-lang/book` (commit `c976903459e37407cfa6964530ea3469957b3549`)
  and copies 112 markdown files plus the **669 listing files** that the chapters actually include
  (copying only referenced listings keeps `data/raw` at ~2.6 MB instead of the full repository).
- `rag/ingest.py` handles mdBook syntax: `{{#include}}` and `{{#rustdoc_include}}` with `:anchor` and `:start:end`
  specs (only the anchored region is inlined; `// ANCHOR:` marker lines are removed). After cleaning,
  **0 unresolved directives** remain.
- Problem found while reading the source: the book now uses a custom `<Listing number=.. file-name=.. caption=..>`
  tag instead of `<span class="filename">`. Both are handled; listing number, file name and caption are kept as text.
- Corpus statistics (`results/corpus_stats.json`): 111 pages, 21 chapters, 8 appendix pages, 201,287 words after
  inlining code, 528 headings, 950 code blocks.

## Phase 2: chunking
- Header-aware: split at headings first (headings inside code fences are ignored, because Rust hidden lines
  start with `#`), keep the heading path and prepend it to every chunk.
- Blocks = paragraphs or whole code fences. Blocks are packed greedily to ~350 estimated tokens
  (tokens = words x 1.3, a documented heuristic, no tokenizer dependency). Overlap is block-level: the trailing
  blocks of a full chunk (up to 15% of the target) start the next chunk; if the last block is too big, its last
  ~40 words are carried instead (prose only, so code is never duplicated in pieces).
- **Problem:** the first run produced a 812-word chunk. Cause: the "Stack and the Heap" blockquote uses `>` lines
  instead of blank lines between paragraphs, so the whole box looked like one paragraph. Fix: treat a bare `>` line
  as a paragraph break, and split any single prose block (e.g. the operator table) that exceeds the limit on line
  boundaries. Max chunk size dropped to 314 words.
- Final stats (`results/chunk_stats.json`): 1,096 chunks, mean 196 words, median 215, min 30, max 314,
  64% contain code.

## Phase 3: embeddings and store
- fastembed `BAAI/bge-small-en-v1.5` (fastembed downloads the quantised ONNX export `Qdrant/bge-small-en-v1.5-onnx-Q`),
  384 dimensions. Query prefix only on queries.
- Chroma PersistentClient, `hnsw:space = cosine`, embeddings passed explicitly. `build_index.py` drops and recreates the
  collection, so it is idempotent.
- Index build: 183 s embedding, 197 s total on CPU (`results/index_stats.json`).

## Phase 4: retrieval
- Dense (Chroma), BM25 (`rank_bm25`), hybrid (RRF, k=60, 20 candidates each, top_k=4).
- BM25 tokenizer keeps Rust identifiers (`vec<t>`, `rc<refcell<t>>`, `&mut`, `std::collections`) and also emits their
  base parts (`vec`, `collections`) so plain-word queries still match. Small stopword list.
- **Relevance-gate tuning** (`scripts/tune_threshold.py`, `results/threshold_tuning.json`, `results/threshold_sweep.png`):
  best dense similarity for answerable questions ranged 0.708-0.892 (mean 0.804), for unanswerable 0.457-0.708
  (mean 0.587). The sweep's objective (correct refusals minus false refusals) peaks at **0.71** (100% correct refusals,
  3.3% false refusals), but at 0.71 the gate separates u10 (0.7076, a Go goroutine question) from q10 (0.7082) by only
  0.0006, which is overfitting to this set. **Chose 0.70**: 0% false refusals, 90% correct refusals by the gate alone;
  the prompt's refusal rule is the second line of defence for borderline off-topic questions.
  *Caveat: the threshold was tuned on the same 40 questions used for evaluation.*

## Phase 5: LLM
- Plain `requests` to `/api/chat`, temperature 0.1, `num_ctx` 4096, `num_predict` 400. Streaming for the UI,
  non-streaming for evaluation. Model name configurable (`--model`, sidebar, or `RAG_LLM_MODEL` env var).
- If Ollama is unreachable, the pipeline returns a labelled extractive fallback and a warning. Verified for real
  (Ollama was down): the Streamlit AppTest run displayed the fallback and the sidebar error, with no exception.

## Phase 6: evaluation
- `eval/questions.json`: 30 answerable questions over ownership, borrowing, slices, structs, enums, modules,
  collections, errors, traits, lifetimes, testing, closures, iterators, smart pointers, concurrency, plus 10 unanswerable.
  Key facts were checked programmatically against the cleaned gold chapter text; one (q10 "every possibility") did not
  match the book's wording and was changed to "all possibilities".
- Retrieval (`results/retrieval_metrics.json`), 30 answerable questions:

  | mode | Hit@1 | Hit@3 | Hit@5 | MRR@10 |
  |---|---|---|---|---|
  | dense | 0.967 | 1.000 | 1.000 | 0.983 |
  | bm25 | 0.600 | 0.867 | 0.933 | 0.737 |
  | hybrid (RRF) | 0.800 | 0.933 | 0.967 | 0.879 |

- **Finding:** on this question set dense retrieval alone is best; plain RRF lets weaker BM25 rankings pull wrong
  chapters up (e.g. q04 "rules of references": BM25 finds no gold chunk in its top 10 because "references"
  appears all over the book). Hybrid is kept as the default because it was specified and is more robust to exact
  identifier queries, but the honest result is reported. Possible fixes: weighted RRF or a cross-encoder reranker.
  The questions are natural-language paraphrases, which favours dense retrieval.

## Phase 7: Streamlit app
- Verified with Streamlit's `AppTest` (runs the script for real): no exceptions, answer path (fallback, since Ollama
  was down), refusal path ("What is the capital of France?" -> refused, best similarity 0.457) and sources panel.
  Also started headless with `streamlit run` and got HTTP 200 on `/_stcore/health`.

## Phase 8: tests
- 18 pytest tests (chunking, ingest, retrieval/RRF, pipeline with stubbed LLM): all pass (`results/pytest_output.txt`).

## Optional: chunk-size ablation
- `scripts/chunk_ablation.py` re-chunks, re-embeds and re-indexes into a temporary Chroma directory for each target
  (results/chunk_ablation.json):

  | target | chunks | hybrid Hit@3 | hybrid MRR@10 | dense Hit@3 | dense MRR@10 |
  |---|---|---|---|---|---|
  | 200 | 1842 | 0.967 | 0.881 | 1.000 | 0.967 |
  | 350 | 1096 | 0.933 | 0.879 | 1.000 | 0.983 |
  | 500 | 817 | 0.933 | 0.852 | 0.933 | 0.893 |

- Kept 350: best dense MRR, hybrid within 0.002 of the 200-token setting, 41% fewer chunks than 200, and 4 chunks still
  fit comfortably in num_ctx=4096. 500 tokens is clearly worse (the gold passage gets diluted inside larger chunks).

## Phase 10: run and ship (status)
- Done: venv, install, fetch, build index, threshold tuning, retrieval evaluation, ablation, pytest, Streamlit smoke test, git commits.
- **Not done yet:** end-to-end answer evaluation (Ollama not installed). `git push` failed with
  "Repository not found": the GitHub repository must be created (or access granted) first.
