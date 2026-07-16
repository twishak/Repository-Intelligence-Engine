import logging

from codebase_agent.config import settings

logger = logging.getLogger(__name__)


class CodeEmbedder:
    """Loads the embedding model once and reuses it for both corpus and query text.

    Must be the same model/instance family used at ingestion time and at query
    time - embeddings from different models are not comparable.
    """

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        batch_size: int | None = None,
    ) -> None:
        self._model_name = model_name or settings.embedding_model_name
        self._device = device or settings.embedding_device
        self._batch_size = batch_size or settings.embedding_batch_size
        self._model = None  # loaded lazily on first use

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        model = self._get_model()
        self._warn_if_truncated(texts)

        vectors = model.encode(
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > self._batch_size,
        )
        return vectors.tolist()

    def _get_model(self):
        if self._model is None:
            import torch
            from sentence_transformers import SentenceTransformer

            device = self._device or ("cuda" if torch.cuda.is_available() else "cpu")
            logger.info("Loading embedding model %s on %s", self._model_name, device)
            # trust_remote_code=True executes custom model code from the HF repo -
            # required because jina-code's ALiBi-based architecture isn't in
            # transformers' built-in model classes. See requirements.txt for the
            # matching transformers pin this code depends on.
            self._model = SentenceTransformer(
                self._model_name, device=device, trust_remote_code=True
            )
        return self._model

    def _warn_if_truncated(self, texts: list[str]) -> None:
        model = self._model
        max_tokens = getattr(model, "max_seq_length", None)
        if max_tokens is None:
            return
        tokenizer = getattr(model, "tokenizer", None)
        if tokenizer is None:
            return
        for text in texts:
            token_count = len(tokenizer.encode(text, add_special_tokens=True))
            if token_count > max_tokens:
                logger.warning(
                    "Chunk (%d tokens) exceeds embedding model max (%d) and will be truncated: %.80s",
                    token_count,
                    max_tokens,
                    text,
                )
