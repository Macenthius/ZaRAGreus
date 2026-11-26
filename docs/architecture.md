# Architecture

```mermaid
flowchart LR
    subgraph Ingestion["Ingestion pipeline (offline: fetch_corpus.py + build_index.py)"]
        A[rust-lang/book<br/>GitHub repo] -->|shallow clone| B[data/raw<br/>111 .md pages + listings]
        B --> C[ingest.py<br/>resolve includes,<br/>strip HTML, metadata]
        C --> D[chunking.py<br/>header-aware,<br/>~350 tok, 15% overlap,<br/>code fences intact]
        D --> E[embeddings.py<br/>fastembed<br/>bge-small-en-v1.5]
        E --> F[(Chroma<br/>chroma_db/<br/>cosine)]
    end

    subgraph Query["Query pipeline (online: pipeline.py)"]
        Q[User question<br/>Streamlit UI] --> QE[embed query<br/>with bge prefix]
        QE --> DR[Dense top-20<br/>Chroma]
        Q --> BR[BM25 top-20<br/>code-aware tokenizer]
        F -.-> DR
        F -.->|all chunks at startup| BR
        DR --> RRF[Reciprocal Rank Fusion<br/>k = 60 -> top_k = 4]
        BR --> RRF
        DR --> G{Relevance gate<br/>best cosine >= 0.70?}
        G -- no --> R[Refuse:<br/>I couldn't find this<br/>in the Rust Book.]
        G -- yes --> P[llm.py prompt builder<br/>numbered context + strict rules]
        RRF --> P
        P --> O[Ollama /api/chat<br/>qwen2.5:0.5b, temp 0.1]
        O -->|stream| UI[Answer with citations<br/>+ sources panel]
        O -. unreachable .-> X[Extractive fallback<br/>best chunk, labelled]
        X --> UI
    end
```

A static PNG of the same flow is at `docs/architecture.png` (drawn with matplotlib by
`scripts/draw_architecture.py`).

## Workflow

**Ingestion (run once)**

1. `scripts/fetch_corpus.py` shallow-clones `rust-lang/book`, copies the 112 `src/*.md` files
   and the 669 listing files they include into `data/raw/`, and records the commit SHA in
   `data/corpus_manifest.json`.
2. `rag/ingest.py` cleans each page: inlines `{{#include}}` / `{{#rustdoc_include}}` directives
   (anchored regions or line ranges only), removes HTML comments, images and `<Listing>` /
   `<span>` wrappers (keeping file names and captions as text), and derives metadata
   (`file`, `chapter_number`, `chapter_title`, `url`). `SUMMARY.md` provides the titles.
3. `rag/chunking.py` splits each page at headings (ignoring `#` lines inside code), then packs
   paragraphs and whole code blocks into chunks of about 350 estimated tokens with about 15%
   overlap, and prepends the heading path (e.g. `Understanding Ownership > References and Borrowing`).
4. `rag/embeddings.py` embeds every chunk with `BAAI/bge-small-en-v1.5` (fastembed, ONNX, 384-d).
5. `rag/store.py` writes ids, texts, metadata and embeddings to a persistent Chroma collection
   using cosine distance.

**Query (per question)**

1. The question is embedded with the bge query prefix and searched in Chroma (dense top-20).
2. The same question is tokenised with a code-aware tokenizer (keeps `Vec<T>`, `&mut`,
   `std::rc`) and scored with BM25 over all chunks (BM25 top-20).
3. Hybrid mode fuses both rankings with Reciprocal Rank Fusion, `score = sum 1/(60 + rank)`,
   and keeps the top 4. (Dense-only and BM25-only modes are also available.)
4. **Relevance gate:** if the best dense cosine similarity is below 0.70, the pipeline returns
   the refusal message without calling the LLM.
5. Otherwise the 4 chunks are numbered `[1]..[4]` and placed in a prompt whose system message
   requires answering only from the context, citing `[n]`, copying code exactly, and replying
   with the exact refusal sentence when the context is insufficient.
6. Ollama (`qwen2.5:0.5b`, temperature 0.1, `num_ctx` 4096, max 400 output tokens) generates
   the answer, streamed to the Streamlit UI. If Ollama cannot be reached, a clearly labelled
   extractive fallback (the best chunk) is shown instead.
7. The UI shows the answer, the latency breakdown, and a sources panel with chapter, heading
   path, scores, a link to the online book page and the full chunk text.
