import logging
from typing import List
import numpy as np

logger = logging.getLogger(__name__)

_model_instance = None
MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384


def get_embedding_model():
    global _model_instance
    if _model_instance is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading SentenceTransformer model '{MODEL_NAME}'...")
            _model_instance = SentenceTransformer(MODEL_NAME)
        except Exception as exc:
            logger.warning(f"Could not load SentenceTransformer '{MODEL_NAME}': {exc}. Using fallback embedding generator.")
            _model_instance = "FALLBACK"
    return _model_instance


class EmbeddingService:
    @staticmethod
    def generate_embeddings(texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        model = get_embedding_model()

        if model != "FALLBACK" and hasattr(model, "encode"):
            try:
                embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
                return embeddings.tolist()
            except Exception as exc:
                logger.error(f"Error generating embeddings via SentenceTransformer: {exc}")

        # Deterministic fallback embedding generator (384d) for offline / testing environments
        fallback_embeddings: List[List[float]] = []
        for text in texts:
            # Seed generator with string hash
            rng = np.random.RandomState(abs(hash(text)) % (2**31 - 1))
            vec = rng.randn(EMBEDDING_DIM)
            vec = vec / (np.linalg.norm(vec) + 1e-9)
            fallback_embeddings.append(vec.tolist())

        return fallback_embeddings

    @staticmethod
    def generate_query_embedding(query_text: str) -> List[float]:
        # BGE models recommend adding query instruction for optimal retrieval performance
        instruction_query = f"Represent this sentence for searching relevant passages: {query_text}"
        res = EmbeddingService.generate_embeddings([instruction_query])
        return res[0] if res else [0.0] * EMBEDDING_DIM
