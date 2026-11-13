import logging
from typing import List, Dict, Optional, Tuple
import tiktoken
from config import Config

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Manages conversational context windows, token budgeting,
    message truncation, and running summary injection.
    """

    def __init__(
        self,
        model: str = Config.OPENAI_MODEL,
        max_context_tokens: int = Config.MAX_CONTEXT_TOKENS,
        max_recent_messages: int = Config.MAX_RECENT_MESSAGES,
        summary_trigger_count: int = Config.SUMMARY_TRIGGER_COUNT,
        reserved_response_tokens: int = Config.RESERVED_RESPONSE_TOKENS,
    ):
        self.model = model
        self.max_context_tokens = max_context_tokens
        self.max_recent_messages = max_recent_messages
        self.summary_trigger_count = summary_trigger_count
        self.reserved_response_tokens = reserved_response_tokens

        # Attempt to load the appropriate tiktoken encoding
        try:
            self.tokenizer = tiktoken.encoding_for_model(self.model)
        except Exception:
            try:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                logger.warning(f"Could not load tiktoken encoding: {e}. Fallback to char estimate.")
                self.tokenizer = None

    def estimate_tokens(self, text: Optional[str]) -> int:
        """
        Estimate token count for a text string.
        Falls back to ~4 characters per token if tokenizer is unavailable.
        """
        if not text:
            return 0
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception:
                pass
        # Fallback estimation: average 4 chars per token + 1 token buffer
        return max(1, len(text) // 4 + 1)

    def estimate_message_tokens(self, message: Dict[str, str]) -> int:
        """
        Estimate tokens for a single OpenAI message object,
        accounting for role overhead (~4 tokens per message).
        """
        # Standard chat completions formatting overhead: <|im_start|>{role}\n{content}<|im_end|>
        overhead = 4
        content_tokens = self.estimate_tokens(message.get("content", ""))
        role_tokens = self.estimate_tokens(message.get("role", ""))
        return overhead + content_tokens + role_tokens

    def needs_summarization(self, total_message_count: int, current_summary: Optional[str]) -> bool:
        """
        Determine if the conversation is long enough to trigger a running summary.
        Triggers when message count exceeds summary_trigger_count.
        """
        return total_message_count > self.summary_trigger_count

    def get_messages_to_summarize(
        self, all_messages: List[Dict[str, str]], keep_recent: int = 6
    ) -> List[Dict[str, str]]:
        """
        Partition messages: returns the older messages that should be incorporated
        into a running summary, while preserving the most recent ones intact.
        """
        if len(all_messages) <= keep_recent:
            return []
        return all_messages[:-keep_recent]

    def build_context_messages(
        self,
        system_prompt: str,
        recent_messages: List[Dict[str, str]],
        summary: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Assembles the contextual messages payload for the OpenAI API:
        1. Always includes the base system prompt.
        2. Injects running summary of prior conversation if present.
        3. Appends recent messages, enforcing the max_recent_messages limit
           and pruning oldest messages if the combined token count exceeds the token budget.
        4. Maintains strict chronological order of conversation.
        """
        # Effective budget for context (leaving room for response generation)
        context_budget = max(500, self.max_context_tokens - self.reserved_response_tokens)

        # 1. Base system prompt
        context_list: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        allocated_tokens = self.estimate_message_tokens(context_list[0])

        # 2. Prepend running conversation summary if available
        if summary and summary.strip():
            summary_message = {
                "role": "system",
                "content": (
                    f"Contextual Memory (Summary of earlier conversation):\n"
                    f"{summary.strip()}\n"
                    f"Use this background context when answering references to past topics."
                ),
            }
            summary_tokens = self.estimate_message_tokens(summary_message)
            context_list.append(summary_message)
            allocated_tokens += summary_tokens

        # 3. Take latest N messages (up to max_recent_messages)
        candidate_messages = recent_messages[-self.max_recent_messages:] if recent_messages else []

        # 4. Token Budget Enforcement:
        # If candidate messages exceed remaining budget, truncate oldest candidate messages
        # while keeping the most recent ones.
        while candidate_messages:
            total_candidate_tokens = sum(
                self.estimate_message_tokens(m) for m in candidate_messages
            )
            if (allocated_tokens + total_candidate_tokens) <= context_budget:
                break
            # If even a single message doesn't fit, keep at least the last user message
            if len(candidate_messages) <= 1:
                break
            # Pop the oldest candidate message to fit budget
            candidate_messages.pop(0)

        # Append candidate messages in chronological order
        context_list.extend(candidate_messages)

        logger.debug(
            f"Context built: {len(context_list)} items, estimated tokens: "
            f"{sum(self.estimate_message_tokens(m) for m in context_list)}"
        )
        return context_list
