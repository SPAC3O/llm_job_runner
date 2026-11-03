import json
import pytest
from types import SimpleNamespace

from unittest.mock import AsyncMock
from contextlib import asynccontextmanager

from worker import consumer
from schemas import JobTaskStatus


@pytest.mark.asyncio
async def test_handle_job_success(
    db_session,
    queued_job,
    monkeypatch,
):
    @asynccontextmanager
    async def mock_session():
        yield db_session

    monkeypatch.setattr(
        consumer,
        "async_session_local",
        mock_session,
    )

    llm_client = AsyncMock()

    llm_client.chat_completion.return_value = SimpleNamespace(
        message="Generated summary",
        latency=500,
        usage=SimpleNamespace(
            prompt_tokens=100,
            completion_tokens=50,
        ),
    )

    message = AsyncMock()
    message.body = json.dumps({"job_id": str(queued_job.id)}).encode()

    await consumer.handle_job(message, llm_client)

    message.ack.assert_awaited_once()
    message.reject.assert_not_awaited()

    llm_client.chat_completion.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_duplicate_delivery(
    db_session,
    queued_job,
    monkeypatch,
):
    @asynccontextmanager
    async def mock_session():
        yield db_session

    monkeypatch.setattr(
        consumer,
        "async_session_local",
        mock_session,
    )

    queued_job.status = JobTaskStatus.running.value
    await db_session.commit()

    llm_client = AsyncMock()

    message = AsyncMock()
    message.body = json.dumps({"job_id": str(queued_job.id)}).encode()

    await consumer.handle_job(message, llm_client)

    message.ack.assert_awaited_once()
    message.reject.assert_not_awaited()

    llm_client.chat_completion.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_job_failure(
    db_session,
    queued_job,
    monkeypatch,
):
    @asynccontextmanager
    async def mock_session():
        yield db_session

    monkeypatch.setattr(
        consumer,
        "async_session_local",
        mock_session,
    )

    llm_client = AsyncMock()

    llm_client.chat_completion.side_effect = RuntimeError("LLM unavailable")

    message = AsyncMock()
    message.body = json.dumps({"job_id": str(queued_job.id)}).encode()

    await consumer.handle_job(message, llm_client)

    message.reject.assert_awaited_once_with(requeue=False)

    message.ack.assert_not_awaited()
