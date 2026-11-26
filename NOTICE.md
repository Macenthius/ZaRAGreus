# Notice: corpus attribution

This project indexes the text of **The Rust Programming Language** ("the Rust Book")
by Steve Klabnik, Carol Nichols and Chris Krycho, with contributions from the Rust Community.

- Source: https://github.com/rust-lang/book (the `src/*.md` chapters and the `listings/` files they include)
- Exact commit used: see `data/corpus_manifest.json`
- Online version: https://doc.rust-lang.org/book/
- Licence: the Rust Book is dual-licensed under the **MIT licence** and the **Apache License, Version 2.0**,
  at your option. Copies of both licences are in the upstream repository
  (`LICENSE-MIT`, `LICENSE-APACHE`).

The files in `data/raw/` are unmodified copies of the upstream files. Cleaning (resolving
include directives, removing HTML) happens at index-build time in `rag/ingest.py`.

This project is not affiliated with or endorsed by the Rust Project or the Rust Foundation.
"Rust" is a trademark of the Rust Foundation.
