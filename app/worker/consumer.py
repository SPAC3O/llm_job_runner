import json
import logging
import uuid
import datetime

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from functools import partial

from db import models, async_session_local
from schemas import JobTaskStatus, LlmMessage, JobTaskType
from core import OpenAIClient, settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rabbitmq")

PROMPT_SUMMARIZATION = "Return a concise summary of a given text."
PROMPT_CLASSIFICATION = "Classify text into a fixed set of categories: 'positive', 'neutral', 'negative', 'mixed'. Return only the category name."
CLASSIFICATION_CATEGORIES = ("positive", "neutral", "negative", "mixed")


def choose_prompt(task_type: str) -> str:
    match task_type:
        case JobTaskType.summarization.value:
            prompt = PROMPT_SUMMARIZATION
        case JobTaskType.classification.value:
            prompt = PROMPT_CLASSIFICATION
        case _:
            prompt = None

    return prompt


def prepare_result(task_type: str, response: str) -> dict:
    match task_type:
        case JobTaskType.summarization.value:
            result_data = {"text": response}
        case JobTaskType.classification.value if response in CLASSIFICATION_CATEGORIES:
            result_data = {"category": response}
        case _:
            result_data = None

    return result_data


async def process_job(
    job_id: uuid.UUID, db: AsyncSession, llm_client: OpenAIClient
) -> None:
    logger.info(f"Processing job: {job_id}")

    result = await db.execute(select(models.Job).where((models.Job.id == job_id)))

    job_existing = result.scalars().first()

    attempt_count = job_existing.attempt_count + 1

    job_attempt = models.JobAttempt(
        id=uuid.uuid4(),
        job_id=job_id,
        attempt_number=attempt_count,
        status=JobTaskStatus.running.value,
    )

    job_existing.attempt_count = attempt_count

    db.add(job_attempt)
    await db.commit()
    await db.refresh(job_attempt)

    try:
        prompt = choose_prompt(job_existing.task_type)
        if prompt is None:
            raise LookupError("Invalid task type")

        response = await llm_client.chat_completion(
            messages=[
                LlmMessage(
                    role="developer",
                    content=prompt,
                ),
                LlmMessage(role="user", content=job_existing.input_data["text"]),
            ],
            model=settings.llm.model,
        )

        result_data = prepare_result(job_existing.task_type, response.message)
        if result_data is None:
            logger.debug(f"Result data: {result_data}")
            raise LookupError("Invalid response")

        job_attempt.finished_at = datetime.datetime.now(datetime.UTC)
        job_attempt.status = JobTaskStatus.succeeded.value
        job_attempt.latency_ms = response.latency
        job_attempt.prompt_tokens = response.usage.prompt_tokens
        job_attempt.completion_tokens = response.usage.completion_tokens

        job_existing.status = JobTaskStatus.succeeded.value
        job_existing.result_data = result_data
        job_existing.prompt_tokens = (
            response.usage.prompt_tokens
            if job_existing.prompt_tokens is None
            else job_existing.prompt_tokens + response.usage.prompt_tokens
        )
        job_existing.completion_tokens = (
            response.usage.completion_tokens
            if job_existing.completion_tokens is None
            else job_existing.completion_tokens + response.usage.completion_tokens
        )

    except Exception as e:
        job_existing.status = JobTaskStatus.failed.value
        job_existing.error_message = str(e)
        job_attempt.status = JobTaskStatus.failed.value
        job_attempt.error_message = str(e)
        job_attempt.finished_at = datetime.datetime.now(datetime.UTC)
        logger.error(
            f"Error occured during making llm call on job with id: {job_id}. Error: {str(e)}"
        )
        await db.commit()
        await db.refresh(job_existing)
        raise

    job_existing.status = JobTaskStatus.succeeded.value
    job_attempt.status = JobTaskStatus.succeeded.value

    await db.commit()
    await db.refresh(job_existing)

    logger.info(f"Finished job: {job_id}")


async def _claim_job(job_id: uuid.UUID, db: AsyncSession) -> bool:
    result = await db.execute(
        update(models.Job)
        .where(
            models.Job.id == job_id,
            models.Job.status == JobTaskStatus.queued.value,
        )
        .values(
            status=JobTaskStatus.running.value,
            result_data=None,
        )
        .returning(models.Job.id)
    )
    claimed_job_id = result.scalar_one_or_none()
    await db.commit()
    return claimed_job_id is not None


async def handle_job(
    message: AbstractIncomingMessage,
    llm_client: OpenAIClient,
) -> None:
    try:
        payload = json.loads(message.body)
        job_id = uuid.UUID(payload["job_id"])

        async with async_session_local() as db:
            if not await _claim_job(job_id, db):
                logger.info(f"Job already claimed or processed: {job_id}")
                await message.ack()
                return

            await process_job(job_id, db, llm_client)

    except Exception:
        logger.exception("Failed to process message")

        await message.reject(requeue=False)

    else:
        await message.ack()
        logger.info("Acknowledged message")


async def consume(
    connection: aio_pika.RobustConnection, queue: str, llm_client: OpenAIClient
) -> None:
    channel = await connection.channel()
    try:
        queue_item = await channel.get_queue(queue)

        logger.info(f"Waiting for jobs on queue: {queue}")

        match queue:
            case "llm_jobs":
                await queue_item.consume(partial(handle_job, llm_client=llm_client))

        await asyncio.Future()
    finally:
        await channel.close()
