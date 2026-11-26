"""Pipeline tests with a stubbed retriever and LLM (no Ollama, no index needed)."""
import config
from rag.llm import LLMUnavailable
from rag.pipeline import RAGPipeline
from rag.retrieval import Hit, RetrievalResult


class StubRetriever:
    def __init__(self, best: float):
        self.best = best

    def retrieve(self, question, mode, top_k, threshold):
        hit = Hit("ch04::000", "Ownership > Rules\n\nEach value in Rust has an owner.",
                  {"heading_path": "Ownership > Rules", "file": "ch04.md"}, dense_score=self.best, rank=1)
        return RetrievalResult([hit], self.best, passed_gate=self.best >= threshold)


class StubLLM:
    def __init__(self, reply="Each value has an owner [1].", fail=False):
        self.reply, self.fail, self.calls = reply, fail, []

    def chat(self, messages, model=None):
        self.calls.append(messages)
        if self.fail:
            raise LLMUnavailable("down")
        return self.reply

    def chat_stream(self, messages, model=None):
        if self.fail:
            raise LLMUnavailable("down")
        yield from self.reply.split(" ")


def test_answer_uses_context_and_cites():
    llm = StubLLM()
    ans = RAGPipeline(StubRetriever(0.9), llm, threshold=0.7).ask("Who owns a value?")
    assert not ans.refused and "[1]" in ans.answer
    user_msg = llm.calls[0][1]["content"]
    assert "[1] (source: Ownership > Rules)" in user_msg and "Who owns a value?" in user_msg
    assert set(ans.latency) == {"retrieve_ms", "generate_ms"}


def test_gate_refuses_without_calling_llm():
    llm = StubLLM()
    ans = RAGPipeline(StubRetriever(0.3), llm, threshold=0.7).ask("Capital of France?")
    assert ans.refused and ans.answer == config.REFUSAL_TEXT
    assert llm.calls == []


def test_llm_refusal_detected():
    ans = RAGPipeline(StubRetriever(0.9), StubLLM(reply=config.REFUSAL_TEXT), threshold=0.7).ask("q")
    assert ans.refused


def test_fallback_when_llm_down():
    ans = RAGPipeline(StubRetriever(0.9), StubLLM(fail=True), threshold=0.7).ask("q")
    assert ans.used_fallback and "Extractive fallback" in ans.answer and ans.warning


def test_stream_fallback_when_llm_down():
    ans, stream = RAGPipeline(StubRetriever(0.9), StubLLM(fail=True), threshold=0.7).ask_stream("q")
    assert "Extractive fallback" in "".join(stream) and ans.used_fallback
