"""Header-aware chunker for the cleaned Rust Book.

Algorithm
1. Split each document into sections at markdown headings (ignoring '#' lines inside code
   fences). Each section remembers its heading path, e.g. "Understanding Ownership >
   References and Borrowing > Mutable References".
2. Split each section into *blocks*: paragraphs, and whole fenced code blocks (a code block
   is never cut unless it alone exceeds the size limit, in which case it is split on lines
   and each piece is re-fenced).
3. Greedily pack blocks into chunks of about CHUNK_TARGET_TOKENS. When a chunk is full, the
   next chunk starts with the trailing blocks of the previous one (~15% overlap).
4. A small trailing chunk is merged into its neighbour; chunks under MIN_CHUNK_WORDS are dropped.
5. The heading path is prepended to the chunk text so each chunk is self-describing.

Tokens are estimated as words * TOKENS_PER_WORD (no tokenizer dependency).
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

import config
from rag.ingest import Document

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass
class Chunk:
    """A retrievable unit of text with metadata."""
    chunk_id: str
    text: str
    metadata: dict = field(default_factory=dict)


def estimate_tokens(text: str) -> int:
    """Word-based token estimate (documented heuristic)."""
    return int(round(len(text.split()) * config.TOKENS_PER_WORD))


def _clean_heading(h: str) -> str:
    return h.replace("`", "").strip()


def split_sections(text: str) -> list[tuple[list[str], str]]:
    """Split markdown into (heading_stack, body) sections, skipping headings in code fences."""
    sections: list[tuple[list[str], str]] = []
    stack: list[tuple[int, str]] = []
    buf: list[str] = []
    in_code = False

    def flush() -> None:
        body = "\n".join(buf).strip()
        if body:
            sections.append(([t for _, t in stack], body))
        buf.clear()

    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
            buf.append(line)
            continue
        m = None if in_code else HEADING_RE.match(line)
        if m:
            flush()
            level, title = len(m.group(1)), _clean_heading(m.group(2))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
        else:
            buf.append(line)
    flush()
    return sections


def split_blocks(body: str, max_tokens: int) -> list[str]:
    """Split a section body into paragraphs and intact code fences."""
    blocks: list[str] = []
    buf: list[str] = []
    in_code = False
    for line in body.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```"):
            if not in_code:  # opening fence: flush prose paragraph first
                if buf:
                    blocks.append("\n".join(buf).strip())
                    buf = []
                in_code = True
                buf.append(line)
            else:  # closing fence: emit the whole code block
                buf.append(line)
                blocks.extend(_split_oversized_code("\n".join(buf), max_tokens))
                buf = []
                in_code = False
            continue
        if not in_code and (not stripped or stripped == ">"):  # blank or empty quote line
            if buf:
                blocks.extend(_split_oversized_prose("\n".join(buf).strip(), max_tokens))
                buf = []
            continue
        buf.append(line)
    if buf:  # unterminated fence or trailing paragraph
        text = "\n".join(buf).strip()
        blocks.extend(_split_oversized_code(text, max_tokens) if in_code
                      else _split_oversized_prose(text, max_tokens))
    return [b for b in blocks if b]


def _split_oversized_prose(block: str, max_tokens: int) -> list[str]:
    """Split a prose block (e.g. a long table) that alone exceeds max_tokens on line boundaries."""
    if estimate_tokens(block) <= max_tokens:
        return [block]
    pieces, cur = [], []
    for ln in block.splitlines():
        cur.append(ln)
        if estimate_tokens("\n".join(cur)) >= max_tokens:
            pieces.append("\n".join(cur))
            cur = []
    if cur:
        pieces.append("\n".join(cur))
    return pieces


def _split_oversized_code(block: str, max_tokens: int) -> list[str]:
    """Keep a code block whole unless it alone exceeds max_tokens; then split on lines and re-fence."""
    if estimate_tokens(block) <= max_tokens:
        return [block]
    lines = block.splitlines()
    fence_open, body = lines[0], lines[1:-1]
    pieces, cur = [], []
    for ln in body:
        cur.append(ln)
        if estimate_tokens("\n".join(cur)) >= max_tokens:
            pieces.append(cur)
            cur = []
    if cur:
        pieces.append(cur)
    return [f"{fence_open}\n" + "\n".join(p) + "\n```" for p in pieces]


def pack_blocks(blocks: list[str], target_tokens: int, overlap_ratio: float) -> list[list[str]]:
    """Greedy packing of blocks into chunks with block-level overlap."""
    overlap_tokens = int(target_tokens * overlap_ratio)
    chunks: list[list[str]] = []
    cur: list[str] = []
    cur_tokens = 0
    for block in blocks:
        bt = estimate_tokens(block)
        if cur and cur_tokens + bt > target_tokens:
            chunks.append(cur)
            # carry trailing blocks as overlap (only if they fit inside the overlap budget,
            # so a huge code block is not duplicated)
            carry: list[str] = []
            carry_tokens = 0
            for prev in reversed(cur):
                pt = estimate_tokens(prev)
                if carry_tokens + pt > overlap_tokens:
                    break
                carry.insert(0, prev)
                carry_tokens += pt
            # if the last block is too big to carry, carry its tail words (prose only)
            if not carry and not cur[-1].lstrip().startswith("```"):
                tail = cur[-1].split()[-max(1, int(overlap_tokens / config.TOKENS_PER_WORD)):]
                carry = ["... " + " ".join(tail)]
                carry_tokens = estimate_tokens(carry[0])
            cur, cur_tokens = carry, carry_tokens
        cur.append(block)
        cur_tokens += bt
    if cur:
        chunks.append(cur)
    return chunks


def chunk_document(doc: Document, target_tokens: int = config.CHUNK_TARGET_TOKENS,
                   overlap_ratio: float = config.CHUNK_OVERLAP_RATIO,
                   min_words: int = config.MIN_CHUNK_WORDS) -> list[Chunk]:
    """Chunk one cleaned document."""
    out: list[Chunk] = []
    for heads, body in split_sections(doc.text):
        heading_path = " > ".join(_dedupe_path([doc.metadata["chapter_title"], *heads]))
        groups = pack_blocks(split_blocks(body, target_tokens), target_tokens, overlap_ratio)
        # merge a tiny trailing chunk into its neighbour
        if len(groups) > 1 and sum(len(b.split()) for b in groups[-1]) < min_words * 2:
            tail = groups.pop()
            groups[-1].extend(b for b in tail if b not in groups[-1])
        for blocks in groups:
            body_text = "\n\n".join(blocks)
            n_words = len(body_text.split())
            if n_words < min_words:
                continue
            text = f"{heading_path}\n\n{body_text}"
            meta = {
                **doc.metadata,
                "heading_path": heading_path,
                "n_words": n_words,
                "has_code": "```" in body_text,
            }
            out.append(Chunk("", text, meta))
    for i, ch in enumerate(out):
        digest = hashlib.md5(ch.text.encode("utf-8")).hexdigest()[:6]
        ch.chunk_id = f"{doc.metadata['file'].removesuffix('.md')}::{i:03d}::{digest}"
        ch.metadata["chunk_id"] = ch.chunk_id
    return out


def _dedupe_path(parts: list[str]) -> list[str]:
    """Drop consecutive duplicates (chapter title often equals the page's first heading)."""
    result: list[str] = []
    for p in parts:
        if p and (not result or result[-1].lower() != p.lower()):
            result.append(p)
    return result


def chunk_documents(docs: list[Document], **kwargs) -> list[Chunk]:
    """Chunk every document."""
    chunks: list[Chunk] = []
    for d in docs:
        chunks.extend(chunk_document(d, **kwargs))
    return chunks


def chunk_stats(chunks: list[Chunk]) -> dict:
    """Summary statistics for results/chunk_stats.json."""
    import statistics as st
    words = [c.metadata["n_words"] for c in chunks]
    tokens = [estimate_tokens(c.text) for c in chunks]
    return {
        "chunk_count": len(chunks),
        "target_tokens": config.CHUNK_TARGET_TOKENS,
        "overlap_ratio": config.CHUNK_OVERLAP_RATIO,
        "tokens_per_word_estimate": config.TOKENS_PER_WORD,
        "words_mean": round(st.mean(words), 1),
        "words_median": st.median(words),
        "words_min": min(words),
        "words_max": max(words),
        "est_tokens_mean_incl_heading": round(st.mean(tokens), 1),
        "pct_with_code": round(100 * sum(c.metadata["has_code"] for c in chunks) / len(chunks), 1),
    }
