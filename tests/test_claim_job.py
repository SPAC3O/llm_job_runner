import pytest

from worker.consumer import _claim_job
from schemas import JobTaskStatus


@pytest.mark.anyio
async def test_claim_queued_job(db_session, queued_job):

    result = await _claim_job(
        queued_job.id,
        db_session,
    )

    await db_session.refresh(queued_job)

    assert result is True
    assert queued_job.status == JobTaskStatus.running.value


@pytest.mark.anyio
async def test_cannot_claim_running_job(db_session, queued_job):

    queued_job.status = JobTaskStatus.running.value
    await db_session.commit()

    result = await _claim_job(
        queued_job.id,
        db_session,
    )

    assert result is False


@pytest.mark.anyio
async def test_cannot_claim_nonexistent_job(db_session):

    import uuid

    result = await _claim_job(
        uuid.uuid4(),
        db_session,
    )

    assert result is False
