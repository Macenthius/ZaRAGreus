"""Thin wrapper around fastembed (ONNX, no torch) for bge-small-en-v1.5."""
from __future__ import annotations

import logging

import numpy as np
from fastembed import TextEmbedding

import config

log = logging.getLogger(__name__)


class Embedder:
    """Embeds passages and queries. Queries get the bge retrieval prefix; passages do not."""

    def __init__(self, model_name: str = config.EMBED_MODEL) -> None:
        log.info("Loading embedding model %s", model_name)
        self.model_name = model_name
        self._model = TextEmbedding(model_name=model_name)

    def embed_passages(self, texts: list[str], batch_size: int = config.EMBED_BATCH_SIZE) -> np.ndarray:
        """Embed document chunks (L2-normalised by the model)."""
        return np.array(list(self._model.embed(texts, batch_size=batch_size)), dtype=np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        """Embed a single query with the bge instruction prefix."""
        return np.array(next(iter(self._model.embed([config.QUERY_PREFIX + text]))), dtype=np.float32)
