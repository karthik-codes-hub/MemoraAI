import logging
from typing import List, Dict, Optional, Tuple
import openai
from openai import OpenAI
from flask import has_app_context, current_app
from config import Config

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Custom exception for user-friendly AI service errors."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class OpenAIService:
    """Service wrapping OpenAI SDK with comprehensive error handling and context tools."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        configured_key = None
        configured_model = None
        if has_app_context():
            configured_key = current_app.config.get("OPENAI_API_KEY")
            configured_model = current_app.config.get("OPENAI_MODEL")

        self.api_key = (api_key or configured_key or Config.OPENAI_API_KEY or "").strip()
        self.model = (model or configured_model or Config.OPENAI_MODEL or "gpt-4o-mini").strip()
        self._client: Optional[OpenAI] = None

    def get_client(self) -> OpenAI:
        """Initialize or retrieve OpenAI client, validating API key presence."""
        if not self.api_key:
            raise AIServiceError(
                "OpenAI API key is missing. Please configure OPENAI_API_KEY in your .env file or application settings.",
                status_code=401,
            )

        if self._client is None:
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def is_configured(self) -> bool:
        """Check if an API key is present."""
        return bool(self.api_key)

    def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Tuple[str, Dict]:
        """
        Sends context messages to OpenAI Chat Completions API and returns response text and token usage.
        """
        client = self.get_client()
        target_model = model or self.model

        try:
            kwargs = {
                "model": target_model,
                "messages": messages,
                "temperature": temperature,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            response = client.chat.completions.create(**kwargs)

            choice = response.choices[0]
            content = choice.message.content or ""
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }
            return content.strip(), usage

        except openai.AuthenticationError as e:
            logger.error(f"OpenAI Authentication Error: {e}")
            raise AIServiceError(
                "Invalid OpenAI API key. Please check your credentials in the .env configuration.",
                status_code=401,
            )
        except openai.RateLimitError as e:
            logger.error(f"OpenAI Rate Limit Error: {e}")
            raise AIServiceError(
                "Your API request limit or quota has been reached. Please check your OpenAI account billing.",
                status_code=429,
            )
        except openai.APITimeoutError as e:
            logger.error(f"OpenAI Timeout Error: {e}")
            raise AIServiceError(
                "Request to the AI service timed out. Please try again.",
                status_code=504,
            )
        except openai.APIConnectionError as e:
            logger.error(f"OpenAI Connection Error: {e}")
            raise AIServiceError(
                "Unable to connect to the AI service. Please check your network connection and try again.",
                status_code=502,
            )
        except openai.BadRequestError as e:
            logger.error(f"OpenAI Bad Request Error: {e}")
            raise AIServiceError(
                f"The AI request was rejected by the service: {e.message}",
                status_code=400,
            )
        except openai.OpenAIError as e:
            logger.error(f"OpenAI Generic Error: {e}")
            raise AIServiceError(
                "An error occurred while communicating with the AI service. Please try again.",
                status_code=500,
            )
        except Exception as e:
            logger.error(f"Unexpected Error during OpenAI completion: {e}", exc_info=True)
            raise AIServiceError(
                "An unexpected server error occurred. Your conversation state is preserved.",
                status_code=500,
            )

    def generate_summary(
        self,
        messages_to_summarize: List[Dict[str, str]],
        existing_summary: Optional[str] = None,
    ) -> str:
        """
        Creates or updates a running concise summary of older conversation turns.
        """
        client = self.get_client()

        dialogue_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in messages_to_summarize
        )

        prompt = (
            "Summarize the key facts, user preferences, names, topics, and important context "
            "from the following conversation segment. Be concise, factual, and retain critical details "
            "so the conversational assistant can accurately reference them later.\n\n"
        )

        if existing_summary:
            prompt += f"Existing Summary:\n{existing_summary}\n\nAdditional New Dialogue to Incorporate:\n{dialogue_text}"
        else:
            prompt += f"Dialogue to Summarize:\n{dialogue_text}"

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a concise context summarization assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=400,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as e:
            logger.warning(f"Could not generate conversation summary: {e}")
            # If summary generation fails, return existing or lightweight fallback without breaking chat flow
            if existing_summary:
                return existing_summary
            return ""

    def generate_title(self, first_user_message: str) -> str:
        """
        Generates a concise 3-5 word title for a new conversation based on the first message.
        """
        if not self.is_configured():
            # Fallback title if API key is not yet set
            clean = " ".join(first_user_message.strip().split())
            return clean[:35] + ("..." if len(clean) > 35 else "")

        try:
            client = self.get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Generate a concise, professional title (3 to 5 words max, no quotes, no period) "
                            "summarizing the topic of this user's message."
                        ),
                    },
                    {"role": "user", "content": first_user_message},
                ],
                temperature=0.5,
                max_tokens=20,
            )
            title = (response.choices[0].message.content or "").strip().strip('"').strip("'")
            return title if title else "New Conversation"
        except Exception as e:
            logger.debug(f"Title generation fallback: {e}")
            clean = " ".join(first_user_message.strip().split())
            return clean[:35] + ("..." if len(clean) > 35 else "")
