from pydantic import BaseModel


class LlmMessage(BaseModel):
    role: str
    content: str


class LlmUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int


class LlmMessageResponse(BaseModel):
    message: str
    usage: LlmUsage
    latency: float
