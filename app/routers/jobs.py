from typing import Annotated
from fastapi import APIRouter, HTTPException, status, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import uuid
import logging

from db import get_session, models
from schemas import (
    JobRequest,
    JobResponse,
    JobTaskStatus,
    JobQueue,
    JobTaskType,
    JobResponseResultData,
    JobUsage,
)
import worker
from core import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jobs")

router = APIRouter()


# TODO
async def enforce_idempotency(
    idempotency_key: str = Header(None, alias="Idempotency-Key"),
):
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required 'Idempotency-Key' header.",
        )

    return idempotency_key.strip()


# TODO
@router.post("", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    request: Request,
    job: JobRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    idempotency_key: str = Depends(enforce_idempotency),
):
    result = await db.execute(
        select(models.Job).where((models.Job.idempotency_key == idempotency_key))
    )
    job_existing = result.scalars().first()

    if job_existing is not None:
        return job_existing

    match job.task_type:
        case JobTaskType.summarization:
            input = job.input.text.strip()
            if input is None or not len(input):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No input were given",
                )
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task type not implemented",
            )

    job_id = uuid.uuid4()
    job_new = models.Job(
        id=job_id,
        task_type=job.task_type.value,
        status=JobTaskStatus.queued.value,
        input_data=job.input.model_dump(),
        idempotency_key=idempotency_key,
        attempt_count=1,
        max_attempts=5,
    )

    db.add(job_new)
    await db.commit()
    await db.refresh(job_new)

    await worker.publish_message(
        connection=request.app.state.rabbitmq,
        msg=str(JobQueue(job_id=job_id).model_dump_json()),
        queue=settings.queue.llm_jobs_queue,
    )

    return job_new


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_session)]):
    result = await db.execute(select(models.Job).where((models.Job.id == job_id)))
    job = result.scalars().first()

    result = await db.execute(
        select(models.JobAttempt)
        .where((models.JobAttempt.job_id == job_id))
        .order_by(models.JobAttempt.attempt_number.desc())
    )

    job_attempt = result.scalars().first()
    if job_attempt is not None:
        prompt_tokens = job_attempt.prompt_tokens
        completion_tokens = job_attempt.completion_tokens
    else:
        prompt_tokens = None
        completion_tokens = None

    if result:
        return JobResponse(
            id=job.id,
            status=job.status,
            task_type=job.task_type,
            attempt_count=job.attempt_count,
            max_attempts=job.max_attempts,
            result_data=JobResponseResultData(
                response=job.result_data,
                usage=JobUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                ),
            ),
        )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")


@router.post(
    "/{job_id}/retry", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED
)
async def retry_job(
    request: Request,
    job_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
):
    result = await db.execute(select(models.Job).where((models.Job.id == job_id)))
    job = result.scalars().first()

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    if job.status != JobTaskStatus.failed.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed jobs can be retried.",
        )

    if job.max_attempts <= job.attempt_count:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Used max retry attempts."
        )

    job.status = JobTaskStatus.queued.value
    job.error_message = None

    await db.commit()
    await db.refresh(job)

    await worker.publish_message(
        connection=request.app.state.rabbitmq,
        msg=str(JobQueue(job_id=job.id).model_dump_json()),
        queue=settings.queue.llm_jobs_queue,
    )

    return job
