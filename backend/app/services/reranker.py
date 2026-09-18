import logging
from typing import List, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)

_reranker_instance = None
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def get_reranker_model():
    global _reranker_instance
    if _reranker_instance is None:
        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading CrossEncoder model '{RERANKER_MODEL_NAME}'...")
            _reranker_instance = CrossEncoder(RERANKER_MODEL_NAME)
        except Exception as exc:
            logger.warning(f"Could not load CrossEncoder '{RERANKER_MODEL_NAME}': {exc}. Using fallback reranker.")
            _reranker_instance = "FALLBACK"
    return _reranker_instance


class CrossEncoderReranker:
    @staticmethod
    def rerank(query: str, candidates: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        model = get_reranker_model()

        if model != "FALLBACK" and hasattr(model, "predict"):
            try:
                pairs = [[query, c.get("content", "")] for c in candidates]
                scores = model.predict(pairs)
                
                for idx, score in enumerate(scores):
                    candidates[idx]["rerank_score"] = float(score)

                sorted_candidates = sorted(candidates, key=lambda x: x.get("rerank_score", 0.0), reverse=True)
                return sorted_candidates[:top_n]
            except Exception as exc:
                logger.error(f"Error reranking candidates via CrossEncoder: {exc}")

        # Fallback Reranking heuristic: RRF score or token match overlap density
        for c in candidates:
            content = c.get("content", "").lower()
            query_words = [w.lower() for w in query.split() if len(w) > 2]
            match_count = sum(1 for w in query_words if w in content)
            base_score = c.get("rrf_score", c.get("similarity_score", 0.5))
            c["rerank_score"] = float(base_score + (match_count * 0.1))

        sorted_candidates = sorted(candidates, key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        return sorted_candidates[:top_n]
