import os
import uuid
import pytest
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.pool import NullPool
from collections.abc import AsyncGenerator
from dotenv import load_dotenv

load_dotenv(".env.test", override=True)

from db import models
from db.models import Base
from schemas import JobTaskStatus


@pytest.fixture(scope="session")
def test_engine():
    engine = create_async_engine(
        os.environ["DATABASE_URL"],
        poolclass=NullPool,
    )
    return engine


@pytest.fixture(scope="session")
async def setup_database(test_engine):
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest.fixture
async def db_session(
    test_engine,
    setup_database,
) -> AsyncGenerator[AsyncSession]:
    conn = await test_engine.connect()
    trans = await conn.begin()

    test_async_session = async_sessionmaker(
        bind=conn,
        class_=AsyncSession,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    async with test_async_session() as session:
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
            await conn.close()


@pytest.fixture
async def queued_job(db_session):
    job = models.Job(
        id=uuid.uuid4(),
        task_type="summary",
        status=JobTaskStatus.queued.value,
        input_data={"text": "Test input"},
        idempotency_key=str(uuid.uuid4()),
        attempt_count=0,
        max_attempts=3,
    )

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    return job
