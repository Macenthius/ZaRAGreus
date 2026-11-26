"""Load and clean the Rust Book markdown (mdBook source) into plain documents.

Cleaning steps
1. Resolve `{{#include path[:anchor|:start:end]}}` and `{{#rustdoc_include ...}}` by inlining
   the referenced listing file (only the anchored region if an anchor is given).
   Directives whose file is missing are dropped.
2. Remove HTML comments, <img> tags and <Listing>/<span> wrappers, keeping useful text
   (listing number, file name, caption) as plain text.
3. Code fences are left intact.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import config

log = logging.getLogger(__name__)

DIRECTIVE_RE = re.compile(r"\{\{#(rustdoc_include|include)\s+([^}]+?)\s*\}\}")
ANCHOR_LINE_RE = re.compile(r"^\s*(//|#)\s*ANCHOR(_END)?:\s*\w+\s*$")
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
IMG_RE = re.compile(r"<img\b[^>]*?/?>", re.DOTALL | re.IGNORECASE)
SPAN_FILENAME_RE = re.compile(r'<span class="filename">(.*?)</span>', re.DOTALL)
SPAN_RE = re.compile(r"<span[^>]*>(.*?)</span>", re.DOTALL)
LISTING_OPEN_RE = re.compile(r"<Listing([^>]*)>")
LISTING_CLOSE_RE = re.compile(r"</Listing>")
ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
OTHER_TAG_RE = re.compile(r"</?(?:div|sup|a|p|br|table|tr|td|th)\b[^>]*>", re.IGNORECASE)
CHAPTER_RE = re.compile(r"^ch(\d+)-")
SUMMARY_LINK_RE = re.compile(r"\[(.+?)\]\((.+?\.md)\)")


@dataclass
class Document:
    """A cleaned book page plus its metadata."""
    text: str
    metadata: dict = field(default_factory=dict)


# ----------------------------------------------------------------- directives
def _extract_region(lines: list[str], spec: str | None) -> list[str]:
    """Return the lines selected by an mdBook include spec (anchor name or line range)."""
    if spec:
        parts = spec.split(":")
        if all(p.isdigit() or p == "" for p in parts):  # line range, 1-based inclusive
            start = int(parts[0]) if parts[0] else 1
            end = int(parts[1]) if len(parts) > 1 and parts[1] else len(lines)
            lines = lines[start - 1:end]
        else:
            anchor = parts[0]
            inside, picked = False, []
            for line in lines:
                if re.match(rf"^\s*(//|#)\s*ANCHOR:\s*{re.escape(anchor)}\s*$", line):
                    inside = True
                    continue
                if re.match(rf"^\s*(//|#)\s*ANCHOR_END:\s*{re.escape(anchor)}\s*$", line):
                    inside = False
                    continue
                if inside:
                    picked.append(line)
            if picked:
                lines = picked
    return [ln for ln in lines if not ANCHOR_LINE_RE.match(ln)]


def resolve_directives(text: str, base_dir: Path) -> str:
    """Inline include directives relative to `base_dir`; drop ones whose file is missing."""

    def _sub(match: re.Match) -> str:
        arg = match.group(2).strip()
        path_part, _, spec = arg.partition(":")
        target = (base_dir / path_part).resolve()
        if not target.is_file():
            log.debug("Missing include target %s", target)
            return ""
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(_extract_region(lines, spec or None)).rstrip()

    return DIRECTIVE_RE.sub(_sub, text)


# ----------------------------------------------------------------- html cleanup
def _listing_header(match: re.Match) -> str:
    attrs = dict(ATTR_RE.findall(match.group(1)))
    bits = []
    if "number" in attrs:
        bits.append(f"Listing {attrs['number']}")
    if "file-name" in attrs:
        bits.append(f"Filename: {attrs['file-name']}")
    if "caption" in attrs:
        bits.append(attrs["caption"])
    return " | ".join(bits)


def clean_markdown(text: str, base_dir: Path) -> str:
    """Apply all cleaning steps to one markdown page."""
    text = COMMENT_RE.sub("", text)
    text = resolve_directives(text, base_dir)
    text = IMG_RE.sub("", text)
    text = SPAN_FILENAME_RE.sub(lambda m: m.group(1).strip(), text)
    text = SPAN_RE.sub(lambda m: m.group(1).strip(), text)
    text = LISTING_OPEN_RE.sub(_listing_header, text)
    text = LISTING_CLOSE_RE.sub("", text)
    text = OTHER_TAG_RE.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ----------------------------------------------------------------- metadata
def load_chapter_titles(raw_dir: Path) -> dict[str, str]:
    """Map file name -> page title using SUMMARY.md."""
    summary = raw_dir / "SUMMARY.md"
    if not summary.exists():
        return {}
    return {f: t.replace("`", "") for t, f in SUMMARY_LINK_RE.findall(summary.read_text(encoding="utf-8"))}


def make_metadata(file_name: str, titles: dict[str, str]) -> dict:
    """Derive file, chapter_number, chapter_title and online url for a page."""
    stem = Path(file_name).stem
    m = CHAPTER_RE.match(stem)
    if m:
        chapter_number = int(m.group(1))
    elif stem.startswith("appendix"):
        chapter_number = 100  # appendices sorted after chapters
    else:
        chapter_number = 0
    # Chapter title = title of the chapter's "-00-" landing page (e.g. ch04-00 -> Understanding Ownership)
    chapter_title = titles.get(file_name, stem)
    if m:
        landing = next((f for f in titles if f.startswith(f"ch{m.group(1)}-00")), None)
        if landing:
            chapter_title = titles[landing]
    return {
        "file": file_name,
        "chapter_number": chapter_number,
        "chapter_title": chapter_title,
        "page_title": titles.get(file_name, stem),
        "url": f"{config.BOOK_ONLINE_BASE}/{stem}.html",
    }


def load_documents(raw_dir: Path = config.RAW_DIR) -> list[Document]:
    """Load every markdown page (except SUMMARY.md) as a cleaned Document."""
    titles = load_chapter_titles(raw_dir)
    # Include paths are written relative to the book's src/ dir (e.g. ../listings/...),
    # and we copied listings/ to raw_dir/listings, so resolve against a virtual src/ subdir.
    base_dir = raw_dir / "src"
    docs: list[Document] = []
    for path in sorted(raw_dir.glob("*.md")):
        if path.name == "SUMMARY.md":
            continue
        cleaned = clean_markdown(path.read_text(encoding="utf-8"), base_dir)
        if cleaned:
            docs.append(Document(cleaned, make_metadata(path.name, titles)))
    log.info("Loaded %d documents from %s", len(docs), raw_dir)
    return docs


def corpus_stats(docs: list[Document]) -> dict:
    """Simple corpus statistics for the report."""
    words = headings = code_blocks = 0
    for d in docs:
        words += len(d.text.split())
        in_code = False
        for line in d.text.splitlines():
            if line.lstrip().startswith("```"):
                if not in_code:
                    code_blocks += 1
                in_code = not in_code
            elif not in_code and re.match(r"^#{1,6}\s", line):
                headings += 1
    chapters = sorted({d.metadata["chapter_number"] for d in docs if 0 < d.metadata["chapter_number"] < 100})
    return {
        "documents": len(docs),
        "chapters": len(chapters),
        "appendix_pages": sum(1 for d in docs if d.metadata["chapter_number"] == 100),
        "words_after_cleaning": words,
        "headings": headings,
        "code_blocks": code_blocks,
        "unresolved_directives": sum(len(DIRECTIVE_RE.findall(d.text)) for d in docs),
    }
