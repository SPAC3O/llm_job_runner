import pytest
from unittest.mock import AsyncMock
from types import SimpleNamespace
from sqlalchemy import select

from db import models
from schemas import JobTaskStatus
from worker.consumer import process_job


@pytest.mark.asyncio
async def test_process_job_success(db_session, queued_job):
    llm_client = AsyncMock()

    llm_client.chat_completion.return_value = SimpleNamespace(
        message="Generated summary",
        latency=1250,
        usage=SimpleNamespace(
            prompt_tokens=100,
            completion_tokens=50,
        ),
    )

    await process_job(
        queued_job.id,
        db_session,
        llm_client,
    )

    await db_session.refresh(queued_job)

    assert queued_job.status == JobTaskStatus.succeeded.value
    assert queued_job.result_data == {"text": "Generated summary"}

    assert queued_job.prompt_tokens == 100
    assert queued_job.completion_tokens == 50

    llm_client.chat_completion.assert_awaited_once()

    result = await db_session.execute(
        select(models.JobAttempt).where(models.JobAttempt.job_id == queued_job.id)
    )

    attempt = result.scalars().one()

    assert attempt.status == JobTaskStatus.succeeded.value
    assert attempt.latency_ms == 1250
    assert attempt.prompt_tokens == 100
    assert attempt.completion_tokens == 50
    assert attempt.finished_at is not None


@pytest.mark.asyncio
async def test_process_job_failure(db_session, queued_job):

    llm_client = AsyncMock()

    llm_client.chat_completion.side_effect = RuntimeError("OpenAI API unavailable")
    with pytest.raises(RuntimeError):
        await process_job(
            queued_job.id,
            db_session,
            llm_client,
        )

    await db_session.refresh(queued_job)

    assert queued_job.status == JobTaskStatus.failed.value
    assert queued_job.error_message == "OpenAI API unavailable"

    result = await db_session.execute(
        select(models.JobAttempt).where(models.JobAttempt.job_id == queued_job.id)
    )

    attempt = result.scalars().one()

    assert attempt.status == JobTaskStatus.failed.value
    assert attempt.error_message == "OpenAI API unavailable"
    assert attempt.finished_at is not None
