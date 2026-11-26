"""Central configuration: every tunable for the Rust Book RAG lives here."""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
MANIFEST_PATH = DATA_DIR / "corpus_manifest.json"
CHROMA_DIR = ROOT / "chroma_db"
RESULTS_DIR = ROOT / "results"
EVAL_PATH = ROOT / "eval" / "questions.json"

# ---------------------------------------------------------------- corpus
BOOK_REPO_URL = "https://github.com/rust-lang/book"
BOOK_ONLINE_BASE = "https://doc.rust-lang.org/book"

# ---------------------------------------------------------------- chunking
# Tokens are estimated as words * TOKENS_PER_WORD (a simple, documented heuristic:
# English prose plus Rust code averages roughly 1.3 sub-word tokens per whitespace word).
TOKENS_PER_WORD = 1.3
CHUNK_TARGET_TOKENS = 350
CHUNK_OVERLAP_RATIO = 0.15
MIN_CHUNK_WORDS = 30          # chunks smaller than this are merged or dropped

# ---------------------------------------------------------------- embeddings / store
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
EMBED_BATCH_SIZE = 64
COLLECTION_NAME = "rust_book"

# ---------------------------------------------------------------- retrieval
RETRIEVAL_MODE = "hybrid"      # dense | bm25 | hybrid
TOP_K = 4
CANDIDATES_PER_RETRIEVER = 20  # dense top-20 and BM25 top-20 go into RRF
RRF_K = 60
# Refuse without calling the LLM when the best dense cosine similarity is below this.
# Tuned on eval/questions.json by scripts/tune_threshold.py (see docs/DEV_LOG.md).
RELEVANCE_THRESHOLD = 0.70

# ---------------------------------------------------------------- LLM
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("RAG_LLM_MODEL", "qwen2.5:0.5b")
LLM_TEMPERATURE = 0.1
LLM_NUM_CTX = 4096
LLM_MAX_TOKENS = 400
LLM_TIMEOUT_S = 180
REFUSAL_TEXT = "I couldn't find this in the Rust Book."
FALLBACK_MAX_WORDS = 160
