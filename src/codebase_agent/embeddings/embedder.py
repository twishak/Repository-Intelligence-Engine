import logging

from tqdm.auto import tqdm, trange

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
        texts, token_lengths = self._truncate_and_measure(texts)

        # sentence-transformers' own encode() sorts by len(text) (characters)
        # to group similarly-sized inputs before padding - a decent proxy in
        # general, but code chunks vary enough that it isn't reliable: one
        # outlier (e.g. a large class's method-signature skeleton) can still
        # land in the same padded batch as much shorter chunks. Bucketing by
        # real token length here, then calling encode() once per bucket,
        # bounds each batch's padding to chunks of genuinely similar length.
        order = sorted(range(len(texts)), key=lambda i: token_lengths[i])
        vectors: list[list[float] | None] = [None] * len(texts)

        show_progress_bar = len(texts) > self._batch_size
        for start in trange(
            0,
            len(order),
            self._batch_size,
            desc="Batches",
            disable=not show_progress_bar,
        ):
            batch_indices = order[start : start + self._batch_size]
            batch_texts = [texts[i] for i in batch_indices]
            batch_vectors = model.encode(
                batch_texts,
                batch_size=len(batch_texts),
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            for idx, vector in zip(batch_indices, batch_vectors, strict=True):
                vectors[idx] = vector.tolist()

        return vectors

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

    def _truncate_and_measure(self, texts: list[str]) -> tuple[list[str], list[int]]:
        """Truncate oversized text and return each text's token length.

        Does both in the same pass so `embed()` can batch by real token
        length afterward without tokenizing every chunk a second time.

        jina-code loads with `trust_remote_code=True` (see `_get_model`), so its
        tokenization is custom, ALiBi-based code and isn't guaranteed to enforce
        `max_seq_length` internally the way a standard transformers model would.
        Without truncating here, a single oversized chunk (e.g. a very large
        function or module-level block) reaches `model.encode()` unbounded,
        which can spike attention memory unpredictably - this keeps the bound
        deterministic regardless of what the model does on its own.
        """
        model = self._model
        max_tokens = getattr(model, "max_seq_length", None)
        tokenizer = getattr(model, "tokenizer", None)
        if max_tokens is None or tokenizer is None:
            # No token-level info available - character count is the same
            # proxy sentence-transformers' own internal batching falls back
            # to, and there's nothing to truncate against without a tokenizer.
            return texts, [len(text) for text in texts]

        result_texts = []
        result_lengths = []
        truncated_count = 0
        largest_length = 0
        show_progress_bar = len(texts) > self._batch_size
        for text in tqdm(texts, desc="Tokenizing", disable=not show_progress_bar):
            token_ids = tokenizer.encode(text, add_special_tokens=True)
            length = len(token_ids)
            if length > max_tokens:
                # One INFO line per chunk for anyone digging in with -v; a large
                # repo can have dozens of these, which as individual WARNINGs
                # buried any real signal (and, printed one at a time, visually
                # crowded out the tqdm bars above and below this loop) - so the
                # user-facing signal is the single aggregate warning below instead.
                logger.info(
                    "Chunk (%d tokens) exceeds embedding model max (%d) and will be truncated",
                    length,
                    max_tokens,
                )
                truncated_count += 1
                largest_length = max(largest_length, length)
                text = tokenizer.decode(
                    token_ids[:max_tokens], skip_special_tokens=True
                )
                length = max_tokens
            result_texts.append(text)
            result_lengths.append(length)

        if truncated_count:
            logger.warning(
                "%d of %d chunks exceeded the embedding model's max length (%d tokens) "
                "and were truncated; largest was %d tokens",
                truncated_count,
                len(texts),
                max_tokens,
                largest_length,
            )

        return result_texts, result_lengths
