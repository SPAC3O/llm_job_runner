from __future__ import annotations

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

from sqlalchemy.dialects.postgresql import JSONB

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Uuid,
    Integer,
    String,
    Text,
)

import uuid
import datetime


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "job"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
    )
    task_type: Mapped[str] = mapped_column(String(15), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    input_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    result_data: Mapped[dict] = mapped_column(JSONB, nullable=True, default=None)
    error_message: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    idempotency_key: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, default=None
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=True, default=None)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=True, default=None)

    attempts: Mapped[list[JobAttempt]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )


class JobAttempt(Base):
    __tablename__ = "job_attempt"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job.id"),
        nullable=False,
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    provider_request_id: Mapped[str] = mapped_column(
        String(255), nullable=True, default=None
    )
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=True, default=None)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=True, default=None)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=True, default=None)
    error_message: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC)
    )
    finished_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    job: Mapped[Job] = relationship(back_populates="attempts")
