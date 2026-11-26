"""Chunker tests: code fences never split, overlap present, metadata complete."""
from rag.chunking import chunk_document, estimate_tokens, split_blocks, split_sections
from rag.ingest import Document

META = {"file": "ch99-01-test.md", "chapter_number": 99, "chapter_title": "Test Chapter",
        "page_title": "Test Page", "url": "https://doc.rust-lang.org/book/ch99-01-test.html"}


def _para(n: int, word: str) -> str:
    return " ".join(f"{word}{i}" for i in range(n))


def make_doc() -> Document:
    code = "```rust\n" + "\n".join(f"let x{i} = {i}; // # not a heading" for i in range(40)) + "\n```"
    body = "\n\n".join([_para(80, "alpha"), _para(80, "beta"), code, _para(80, "gamma"), _para(80, "delta"),
                        _para(80, "eps")])
    return Document(f"## Test Page\n\n{body}\n\n### Sub Section\n\n{_para(60, 'zeta')}", dict(META))


def test_code_fences_never_split():
    chunks = chunk_document(make_doc(), target_tokens=200)
    assert len(chunks) > 2
    for ch in chunks:
        assert ch.text.count("```") % 2 == 0, "every chunk must contain whole fences"


def test_headings_inside_code_are_ignored():
    sections = split_sections("## A\n\n```rust\n# hidden line\n```\n\n## B\n\ntext")
    assert [s[0] for s in sections] == [["A"], ["B"]]


def test_overlap_present():
    chunks = [c for c in chunk_document(make_doc(), target_tokens=200) if "Sub Section" not in c.text]
    assert len(chunks) >= 2
    for prev, nxt in zip(chunks, chunks[1:]):
        prev_body = set(prev.text.split("\n\n", 1)[1].split())
        nxt_body = set(nxt.text.split("\n\n", 1)[1].split())
        assert prev_body & nxt_body, "consecutive chunks should share overlapping text"


def test_metadata_complete_and_heading_prepended():
    required = {"chunk_id", "file", "chapter_number", "chapter_title", "heading_path", "url", "n_words", "has_code"}
    chunks = chunk_document(make_doc())
    assert chunks
    for ch in chunks:
        assert required <= set(ch.metadata)
        assert ch.text.startswith(ch.metadata["heading_path"])
        assert ch.metadata["n_words"] >= 30
    assert any(c.metadata["heading_path"] == "Test Chapter > Test Page > Sub Section" for c in chunks)
    assert any(c.metadata["has_code"] for c in chunks)


def test_oversized_code_block_is_split_and_refenced():
    code = "```rust\n" + "\n".join(f"let value_{i} = compute({i}, {i + 1});" for i in range(200)) + "\n```"
    blocks = split_blocks(code, max_tokens=100)
    assert len(blocks) > 1
    for b in blocks:
        assert b.startswith("```rust") and b.endswith("```")
        assert estimate_tokens(b) <= 130
