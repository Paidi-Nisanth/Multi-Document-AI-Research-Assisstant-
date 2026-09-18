import os
import json
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()
from app.config import settings

logger = logging.getLogger(__name__)

# Import Google Generative AI SDK
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    genai = None
    HAS_GENAI = False


class LLMService:
    @staticmethod
    def get_api_key() -> str:
        return (
            os.getenv("GEMINI_API_KEY")
            or getattr(settings, "GEMINI_API_KEY", "")
            or ""
        ).strip()

    @staticmethod
    def get_provider() -> str:
        key = LLMService.get_api_key()
        if key and HAS_GENAI:
            return "gemini"
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            return "openai"
        return "fallback"

    @staticmethod
    async def generate_response(
        system_instruction: str,
        user_prompt: str,
        temperature: float = 0.2
    ) -> str:
        provider = LLMService.get_provider()
        api_key = LLMService.get_api_key()
        logger.info(f"LLMService: generate_response using provider='{provider}'...")

        if provider == "gemini" and api_key:
            try:
                genai.configure(api_key=api_key)
                model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_instruction
                )
                response = model.generate_content(user_prompt)
                return response.text.strip()
            except Exception as exc:
                logger.error(f"Gemini API Error: {exc}")
                return f"Error communicating with Gemini API: {str(exc)}"

        return "Gemini API Key is not configured. Please set GEMINI_API_KEY in backend/.env to enable live AI responses."

    @staticmethod
    async def stream_response(
        system_instruction: str,
        user_prompt: str,
        temperature: float = 0.2
    ) -> AsyncGenerator[str, None]:
        provider = LLMService.get_provider()
        api_key = LLMService.get_api_key()
        logger.info(f"LLMService: stream_response using provider='{provider}'...")

        if provider == "gemini" and api_key:
            try:
                genai.configure(api_key=api_key)
                model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_instruction
                )
                response = model.generate_content(user_prompt, stream=True)
                for chunk in response:
                    if chunk.text:
                        data_frame = json.dumps({"token": chunk.text})
                        yield f"data: {data_frame}\n\n"
                return
            except Exception as exc:
                logger.error(f"Gemini API Streaming Error: {exc}")
                err_msg = f"Error calling Gemini API ({model_name}): {str(exc)}"
                yield f"data: {json.dumps({'token': err_msg})}\n\n"
                return

        no_key_msg = "Gemini API Key is missing. Please set GEMINI_API_KEY in backend/.env."
        yield f"data: {json.dumps({'token': no_key_msg})}\n\n"
