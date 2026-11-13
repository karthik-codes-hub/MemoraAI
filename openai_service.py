import os
import logging
from typing import List, Dict, Optional, Tuple
import requests
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
    """
    Unified AI Service supporting:
    1. Official OpenAI SDK (for OpenAI keys starting with sk-)
    2. Google Gemini Native API (for Gemini keys starting with AIzaSy)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        configured_key = None
        configured_model = None
        configured_base_url = None
        if has_app_context():
            configured_key = (
                current_app.config.get("OPENAI_API_KEY")
                or current_app.config.get("GEMINI_API_KEY")
            )
            configured_model = current_app.config.get("OPENAI_MODEL")
            configured_base_url = current_app.config.get("OPENAI_BASE_URL")

        self.api_key = (
            api_key
            or configured_key
            or Config.OPENAI_API_KEY
            or os.getenv("GEMINI_API_KEY", "")
            or ""
        ).strip()
        self.base_url = (base_url or configured_base_url or Config.OPENAI_BASE_URL or "").strip()

        # Detect provider
        self.is_gemini = self.api_key.startswith("AIzaSy")

        # Determine model
        model_candidate = (model or configured_model or Config.OPENAI_MODEL or "gpt-4o-mini").strip()
        if self.is_gemini:
            # If user configured an OpenAI model name like gpt-4o-mini, default to gemini-3.5-flash-lite
            if model_candidate.startswith("gpt-") or not model_candidate:
                self.model = "gemini-3.5-flash-lite"
            else:
                self.model = model_candidate
        else:
            self.model = model_candidate

        self._client: Optional[OpenAI] = None

    def get_client(self) -> OpenAI:
        """Initialize or retrieve OpenAI client, validating API key presence."""
        if not self.api_key:
            raise AIServiceError(
                "OpenAI API key is missing. Please configure OPENAI_API_KEY in your .env file or application settings.",
                status_code=401,
            )

        if self._client is None:
            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def is_configured(self) -> bool:
        """Check if an API key is present."""
        return bool(self.api_key)

    def _generate_gemini_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Tuple[str, Dict]:
        """Dispatch completion to Google Gemini REST API."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        system_instruction_text = ""
        contents = []

        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")

            if role == "system":
                if system_instruction_text:
                    system_instruction_text += "\n\n" + content
                else:
                    system_instruction_text = content
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})
            else:
                contents.append({"role": "user", "parts": [{"text": content}]})

        # Ensure at least one content item
        if not contents:
            contents.append({"role": "user", "parts": [{"text": "Hello"}]})

        payload = {"contents": contents}
        if system_instruction_text:
            payload["system_instruction"] = {"parts": [{"text": system_instruction_text}]}

        generation_config = {"temperature": temperature}
        if max_tokens:
            generation_config["maxOutputTokens"] = max_tokens
        payload["generationConfig"] = generation_config

        try:
            r = requests.post(url, json=payload, timeout=40)
            if r.status_code == 200:
                data = r.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return "", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

                content_parts = candidates[0].get("content", {}).get("parts", [])
                response_text = "".join(p.get("text", "") for p in content_parts)

                meta = data.get("usageMetadata", {})
                usage = {
                    "prompt_tokens": meta.get("promptTokenCount", 0),
                    "completion_tokens": meta.get("candidatesTokenCount", 0),
                    "total_tokens": meta.get("totalTokenCount", 0),
                }
                return response_text.strip(), usage

            elif r.status_code == 400:
                logger.error(f"Gemini Bad Request: {r.text}")
                raise AIServiceError(f"Gemini API Bad Request: {r.text}", status_code=400)
            elif r.status_code == 403:
                logger.error(f"Gemini Forbidden: {r.text}")
                raise AIServiceError("Invalid Gemini API key or permission denied.", status_code=403)
            elif r.status_code == 429:
                logger.error(f"Gemini Quota Exceeded: {r.text}")
                raise AIServiceError("Gemini API rate limit reached. Please try again shortly.", status_code=429)
            elif r.status_code == 503:
                logger.error(f"Gemini 503 Overloaded: {r.text}")
                raise AIServiceError("The Gemini model is temporarily busy. Please retry in a few moments.", status_code=503)
            else:
                logger.error(f"Gemini error {r.status_code}: {r.text}")
                raise AIServiceError(f"Gemini API returned status {r.status_code}", status_code=500)

        except requests.exceptions.Timeout:
            raise AIServiceError("Request to Google Gemini timed out. Please try again.", status_code=504)
        except requests.exceptions.RequestException as e:
            logger.error(f"Gemini connection error: {e}")
            raise AIServiceError("Unable to connect to Google Gemini. Please check your network.", status_code=502)

    def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Tuple[str, Dict]:
        """
        Sends context messages to OpenAI or Gemini API and returns response text and token usage.
        """
        if self.is_gemini:
            return self._generate_gemini_response(
                messages, temperature=temperature, max_tokens=max_tokens
            )

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
                "Invalid API key. Please check your credentials in .env. "
                "OpenAI API keys start with 'sk-proj-' or 'sk-'. "
                "Google Gemini API keys start with 'AIzaSy'.",
                status_code=401,
            )
        except openai.PermissionDeniedError as e:
            logger.error(f"OpenAI Permission Denied Error: {e}")
            raise AIServiceError(
                f"Permission denied: {e.message or 'Check model permissions and project access'}.",
                status_code=403,
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
        except AIServiceError:
            raise
        except Exception as e:
            logger.error(f"Unexpected Error during AI completion: {e}", exc_info=True)
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

        messages = [
            {"role": "system", "content": "You are a concise context summarization assistant."},
            {"role": "user", "content": prompt},
        ]

        try:
            summary_text, _ = self.generate_chat_response(messages, temperature=0.3, max_tokens=400)
            return summary_text.strip()
        except Exception as e:
            logger.warning(f"Could not generate conversation summary: {e}")
            if existing_summary:
                return existing_summary
            return ""

    def generate_title(self, first_user_message: str) -> str:
        """
        Generates a concise 3-5 word title for a new conversation based on the first message.
        """
        if not self.is_configured():
            clean = " ".join(first_user_message.strip().split())
            return clean[:35] + ("..." if len(clean) > 35 else "")

        messages = [
            {
                "role": "system",
                "content": (
                    "Generate a concise, professional title (3 to 5 words max, no quotes, no period) "
                    "summarizing the topic of this user's message."
                ),
            },
            {"role": "user", "content": first_user_message},
        ]

        try:
            title_text, _ = self.generate_chat_response(messages, temperature=0.5, max_tokens=20)
            clean = title_text.strip().strip('"').strip("'")
            return clean if clean else "New Conversation"
        except Exception as e:
            logger.debug(f"Title generation fallback: {e}")
            clean = " ".join(first_user_message.strip().split())
            return clean[:35] + ("..." if len(clean) > 35 else "")
