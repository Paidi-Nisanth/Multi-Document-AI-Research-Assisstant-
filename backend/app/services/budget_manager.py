import logging
from typing import List, Dict, Any
import tiktoken

logger = logging.getLogger(__name__)


class BudgetManager:
    def __init__(self, model_name: str = "gpt-4o", max_context_tokens: int = 32000):
        self.max_context_tokens = max_context_tokens
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except Exception:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        try:
            return len(self.encoding.encode(text))
        except Exception:
            return len(text.split())

    def fit_sources_under_budget(
        self,
        sources: List[Dict[str, Any]],
        reserved_tokens: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Truncates or drops lowest-ranking source chunks when total token count exceeds budget.
        Gemini supports 1,000,000+ token context windows, so budget is expanded to 32,000+ tokens.
        """
        effective_budget = max(1000, self.max_context_tokens - reserved_tokens)
        fitted_sources: List[Dict[str, Any]] = []
        current_tokens = 0

        for src in sources:
            content = src.get("content", "")
            chunk_tokens = self.count_tokens(content)

            if current_tokens + chunk_tokens <= effective_budget:
                fitted_sources.append(src)
                current_tokens += chunk_tokens
            else:
                # Calculate remaining token space
                rem_tokens = effective_budget - current_tokens
                if rem_tokens >= 50:
                    tokens = self.encoding.encode(content)[:rem_tokens]
                    truncated_content = self.encoding.decode(tokens) + "..."
                    src_copy = dict(src)
                    src_copy["content"] = truncated_content
                    fitted_sources.append(src_copy)
                    current_tokens += len(tokens)
                break

        logger.info(f"BudgetManager: Fitted {len(fitted_sources)} / {len(sources)} source chunks under {effective_budget} tokens budget (Total tokens: {current_tokens}).")
        return fitted_sources
