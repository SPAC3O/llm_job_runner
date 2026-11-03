from openai import AsyncOpenAI

import time

from core import settings
from schemas import LlmMessage, LlmMessageResponse, LlmUsage


class OpenAIClientException(Exception):
    """
    Exception to raise with OpenAIClient
    """

    pass


class OpenAIClient:
    def __init__(self):
        self._client = AsyncOpenAI(
            api_key=settings.llm.api_key,
            base_url=settings.llm.base_url,
            timeout=60,
            max_retries=2,
        )

    async def close(self) -> None:
        await self._client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    @staticmethod
    def _prepare_messages(messages: list[LlmMessage]):
        if not messages:
            raise ValueError("At least one message is required")

        return [
            message.model_dump(mode="json", exclude_none=True) for message in messages
        ]

    async def chat_completion(self, messages: list[LlmMessage], model: str):
        messages_ready = self._prepare_messages(messages)

        start_time = time.perf_counter()

        try:
            completion = await self._client.chat.completions.create(
                model=model,
                messages=messages_ready,
            )

        except Exception as e:
            raise OpenAIClientException(
                f"Exception occured during llm call: {str(e)}"
            ) from e

        latency_ms = (time.perf_counter() - start_time) * 1000

        if not completion.choices:
            raise OpenAIClientException("LLM provider returned no choices")

        message = completion.choices[0].message

        if message.content is None:
            raise OpenAIClientException(
                f"LLM returned no text content "
                f"(finish_reason={completion.choices[0].finish_reason!r})"
            )

        if completion.usage is None:
            raise OpenAIClientException("LLM provider did not return token usage")

        return LlmMessageResponse(
            message=message.content,
            usage=LlmUsage(
                prompt_tokens=completion.usage.prompt_tokens,
                completion_tokens=completion.usage.completion_tokens,
            ),
            latency=latency_ms,
        )
