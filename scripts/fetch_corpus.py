"""Shallow-clone rust-lang/book and copy its markdown chapters + listings into data/raw.

Usage:  python scripts/fetch_corpus.py
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

log = logging.getLogger("fetch_corpus")

INCLUDE_RE = re.compile(r"\{\{#(?:rustdoc_)?include\s+([^}:\s]+)")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tmp = Path(tempfile.mkdtemp(prefix="rustbook_"))
    repo = tmp / "book"
    log.info("Cloning %s (depth 1) ...", config.BOOK_REPO_URL)
    subprocess.run(["git", "clone", "--depth", "1", config.BOOK_REPO_URL, str(repo)], check=True)
    sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True,
                         capture_output=True, text=True).stdout.strip()

    if config.RAW_DIR.exists():
        shutil.rmtree(config.RAW_DIR)
    config.RAW_DIR.mkdir(parents=True)

    src = repo / "src"
    md_files = sorted(src.glob("*.md"))
    words = 0
    needed: set[str] = set()
    for f in md_files:
        text = f.read_text(encoding="utf-8")
        (config.RAW_DIR / f.name).write_text(text, encoding="utf-8")
        if f.name != "SUMMARY.md":
            words += len(text.split())
        for m in INCLUDE_RE.finditer(text):
            needed.add(m.group(1))

    # Copy only the listing files actually referenced by include directives.
    copied = 0
    for rel in sorted(needed):
        source = (src / rel).resolve()
        if not source.is_file():
            continue
        try:
            rel_to_repo = source.relative_to(repo.resolve())  # e.g. listings/ch02/.../main.rs
        except ValueError:
            continue
        dest = config.RAW_DIR / rel_to_repo
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        copied += 1

    manifest = {
        "source_repo": config.BOOK_REPO_URL,
        "commit_sha": sha,
        "markdown_files": len(md_files),
        "indexed_markdown_files": len([f for f in md_files if f.name != "SUMMARY.md"]),
        "listing_files_copied": copied,
        "total_words": words,
        "fetch_date": dt.date.today().isoformat(),
        "licence": "MIT OR Apache-2.0",
    }
    config.MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    log.info("Manifest: %s", manifest)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
