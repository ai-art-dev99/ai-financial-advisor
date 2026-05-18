"""
Anthropic LLM Client
Wraps the Anthropic SDK with streaming support and retry logic.
"""
import logging
from typing import AsyncIterator, List
from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def stream(
        self,
        messages: List[dict],
        system_prompt: str,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        """
        Stream tokens from Claude.
        Yields text chunks as they arrive (Server-Sent Events compatible).
        """
        try:
            async with self._client.messages.stream(
                model=settings.anthropic_model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"LLM stream error: {e}")
            yield f"\n\n[Error communicating with AI: {str(e)}]"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def complete(
        self,
        messages: List[dict],
        system_prompt: str,
        max_tokens: int = 1024,
    ) -> str:
        """
        Non-streaming completion with retry logic.
        Used for internal operations (e.g. portfolio analysis summaries).
        """
        response = await self._client.messages.create(
            model=settings.anthropic_model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text


llm_client = LLMClient()