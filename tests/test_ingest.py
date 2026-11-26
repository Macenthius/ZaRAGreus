"""Ingest tests: include directives resolved, html cleaned, metadata derived."""
from pathlib import Path

from rag.ingest import clean_markdown, make_metadata

LISTING = """use std::io;
// ANCHOR: here
fn main() {
    println!("hi");
}
// ANCHOR_END: here
"""


def _setup(tmp_path: Path) -> Path:
    f = tmp_path / "listings" / "ch01" / "main.rs"
    f.parent.mkdir(parents=True)
    f.write_text(LISTING, encoding="utf-8")
    return tmp_path / "src"


def test_anchor_include_resolved(tmp_path):
    md = "```rust\n{{#rustdoc_include ../listings/ch01/main.rs:here}}\n```"
    out = clean_markdown(md, _setup(tmp_path))
    assert "{{#" not in out
    assert 'println!("hi");' in out
    assert "use std::io" not in out and "ANCHOR" not in out


def test_full_include_and_line_range(tmp_path):
    base = _setup(tmp_path)
    assert "use std::io" in clean_markdown("{{#include ../listings/ch01/main.rs}}", base)
    ranged = clean_markdown("{{#include ../listings/ch01/main.rs:3:3}}", base)
    assert ranged.strip() == "fn main() {"


def test_missing_include_dropped(tmp_path):
    out = clean_markdown("before\n{{#include ../listings/nope.rs}}\nafter", _setup(tmp_path))
    assert "{{#" not in out and "before" in out and "after" in out


def test_html_cleaned_filename_kept(tmp_path):
    md = ('<!-- secret comment -->\n<span class="filename">Filename: src/main.rs</span>\n'
          '<Listing number="1-1" file-name="main.rs" caption="Hello">\n\n```rust\nfn main() {}\n```\n\n</Listing>\n'
          '<img src="x.svg" alt="pic" />')
    out = clean_markdown(md, _setup(tmp_path))
    assert "secret" not in out and "<" not in out
    assert "Filename: src/main.rs" in out
    assert "Listing 1-1" in out and "Filename: main.rs" in out
    assert "```rust\nfn main() {}\n```" in out


def test_metadata():
    titles = {"ch04-00-understanding-ownership.md": "Understanding Ownership",
              "ch04-02-references-and-borrowing.md": "References and Borrowing"}
    m = make_metadata("ch04-02-references-and-borrowing.md", titles)
    assert m["chapter_number"] == 4
    assert m["chapter_title"] == "Understanding Ownership"
    assert m["url"] == "https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html"
