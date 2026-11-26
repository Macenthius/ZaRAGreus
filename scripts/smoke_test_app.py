"""Headless smoke test: run the real Streamlit script (needs Ollama for a generated answer).

Usage:  python scripts/smoke_test_app.py
"""
from pathlib import Path

from streamlit.testing.v1 import AppTest


at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"), default_timeout=300).run()
print("exceptions after load:", list(at.exception))
print("sidebar success:", [s.value for s in at.sidebar.success])
print("sidebar errors:", [e.value for e in at.sidebar.error])
q = "What are the three rules of ownership?"
at.text_input(key="question").input(q).run()
print("exceptions after question:", list(at.exception))
md = [m.value for m in at.markdown]
answer = next((m for m in md if "[1]" in m or "owner" in m.lower()), None)
print("QUESTION:", q)
print("ANSWER (streamed, rendered):", (answer or "<none>")[:700])
print("SOURCES:", [m.split("\n")[0][:110] for m in md if m.startswith("**[")])
print("CAPTIONS:", [c.value for c in at.caption])
print("errors:", [e.value[:120] for e in at.error])
