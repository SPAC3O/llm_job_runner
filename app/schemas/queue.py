from pydantic import BaseModel
import uuid
from enum import Enum


class JobTaskType(Enum):
    summarization = "summarization"
    classification = "classification"
    extraction = "extraction"


class JobTaskStatus(Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class JobRequestInput(BaseModel):
    text: str


class JobRequest(BaseModel):
    task_type: JobTaskType
    input: JobRequestInput


class JobUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class JobQueue(BaseModel):
    job_id: uuid.UUID


# =================== Response =================== #
class JobResponseResultData(BaseModel):
    response: dict | None = None
    usage: JobUsage


class JobResponse(BaseModel):
    id: uuid.UUID
    status: str
    task_type: JobTaskType
    attempt_count: int
    max_attempts: int
    result_data: JobResponseResultData | None = None
    error_message: str | None = None
