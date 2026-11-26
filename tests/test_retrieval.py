"""Retrieval tests: RRF fusion ordering and the code-aware BM25 tokenizer."""
import pytest

from rag.retrieval import rrf_fuse, tokenize


def test_rrf_ordering_toy_example():
    dense = ["a", "b", "c"]
    bm25 = ["b", "c", "d"]
    fused = rrf_fuse([dense, bm25], k=60)
    # b: 1/62 + 1/61 (highest); c: 1/63 + 1/62; a: 1/61; d: 1/63
    assert [d for d, _ in fused] == ["b", "c", "a", "d"]
    assert fused[0][1] == pytest.approx(1 / 62 + 1 / 61)


def test_rrf_single_list_preserves_order():
    assert [d for d, _ in rrf_fuse([["x", "y", "z"]])] == ["x", "y", "z"]


def test_tokenizer_keeps_rust_identifiers():
    toks = tokenize("Use Rc<RefCell<T>> with &mut and Vec<T> from std::collections")
    assert "rc<refcell<t>>" in toks and "rc" in toks
    assert "&mut" in toks
    assert "vec<t>" in toks and "vec" in toks
    assert "std::collections" in toks and "collections" in toks
    assert "with" not in toks  # stopword
