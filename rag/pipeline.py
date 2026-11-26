"""End-to-end RAG pipeline: retrieve -> gate -> generate (or refuse / fall back)."""
from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field

import config
from rag.llm import LLMUnavailable, OllamaClient, build_messages, extractive_fallback
from rag.retrieval import Hit, Retriever

log = logging.getLogger(__name__)


@dataclass
class Answer:
    """The pipeline's result for one question."""
    question: str
    answer: str
    sources: list[Hit]
    refused: bool
    best_dense: float
    mode: str
    model: str
    used_fallback: bool = False
    warning: str | None = None
    latency: dict = field(default_factory=dict)  # retrieve_ms, generate_ms

    def to_dict(self) -> dict:
        d = asdict(self)
        d["sources"] = [asdict(h) for h in self.sources]
        return d


def _passages(hits: list[Hit]) -> list[dict]:
    return [{"text": h.text, "metadata": h.metadata} for h in hits]


class RAGPipeline:
    """Ties the retriever and LLM together. `llm` can be any object with chat/chat_stream."""

    def __init__(self, retriever: Retriever, llm: OllamaClient | None = None,
                 threshold: float = config.RELEVANCE_THRESHOLD) -> None:
        self.retriever = retriever
        self.llm = llm or OllamaClient()
        self.threshold = threshold

    @classmethod
    def from_disk(cls) -> "RAGPipeline":
        """Build the default pipeline from the persisted Chroma index."""
        from rag.embeddings import Embedder
        from rag.store import VectorStore
        return cls(Retriever(VectorStore(), Embedder()))

    def _retrieve(self, question: str, mode: str, top_k: int):
        t0 = time.perf_counter()
        res = self.retriever.retrieve(question, mode=mode, top_k=top_k, threshold=self.threshold)
        return res, (time.perf_counter() - t0) * 1000

    def ask(self, question: str, mode: str = config.RETRIEVAL_MODE, top_k: int = config.TOP_K,
            model: str | None = None) -> Answer:
        """Answer a question (non-streaming)."""
        model = model or config.LLM_MODEL
        res, retrieve_ms = self._retrieve(question, mode, top_k)
        base = dict(question=question, sources=res.hits, best_dense=res.best_dense, mode=mode, model=model)
        if not res.passed_gate:
            return Answer(answer=config.REFUSAL_TEXT, refused=True,
                          latency={"retrieve_ms": retrieve_ms, "generate_ms": 0.0}, **base)
        t1 = time.perf_counter()
        try:
            text = self.llm.chat(build_messages(question, _passages(res.hits)), model=model)
            fallback, warning = False, None
        except LLMUnavailable as exc:
            log.warning("LLM unavailable, using extractive fallback: %s", exc)
            text, fallback, warning = extractive_fallback(_passages(res.hits)), True, f"LLM unavailable: {exc}"
        generate_ms = (time.perf_counter() - t1) * 1000
        refused = config.REFUSAL_TEXT.lower().rstrip(".") in text.lower()
        return Answer(answer=text, refused=refused, used_fallback=fallback, warning=warning,
                      latency={"retrieve_ms": retrieve_ms, "generate_ms": generate_ms}, **base)

    def ask_stream(self, question: str, mode: str = config.RETRIEVAL_MODE, top_k: int = config.TOP_K,
                   model: str | None = None) -> tuple[Answer, Iterator[str]]:
        """Retrieve immediately and return (answer-skeleton, token iterator) for the UI.

        The skeleton has empty `answer`; the caller accumulates the streamed tokens.
        If the gate fails, the iterator yields the refusal text once.
        """
        model = model or config.LLM_MODEL
        res, retrieve_ms = self._retrieve(question, mode, top_k)
        ans = Answer(question=question, answer="", sources=res.hits, refused=not res.passed_gate,
                     best_dense=res.best_dense, mode=mode, model=model,
                     latency={"retrieve_ms": retrieve_ms, "generate_ms": 0.0})
        if not res.passed_gate:
            return ans, iter([config.REFUSAL_TEXT])

        def gen() -> Iterator[str]:
            t1 = time.perf_counter()
            try:
                yield from self.llm.chat_stream(build_messages(question, _passages(res.hits)), model=model)
            except LLMUnavailable as exc:
                ans.used_fallback, ans.warning = True, f"LLM unavailable: {exc}"
                yield extractive_fallback(_passages(res.hits))
            finally:
                ans.latency["generate_ms"] = (time.perf_counter() - t1) * 1000

        return ans, gen()
