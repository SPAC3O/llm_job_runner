from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, status, Depends

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db import async_engine, get_session
from routers import jobs
from core import rabbitmq
from core import OpenAIClient


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # async with async_engine.begin() as conn:
    #     pass

    rabbitmq_connection = await rabbitmq.connect()
    app.state.rabbitmq = rabbitmq_connection

    llm_connection = OpenAIClient()
    app.state.llm = llm_connection

    try:
        yield
    finally:
        await rabbitmq_connection.close()
        await async_engine.dispose()
        await llm_connection.close()


app = FastAPI(lifespan=lifespan)

app.include_router(jobs.router, prefix="/api/v1/job", tags=["job"])


# =================== HEALTH check =================== #
@app.get("/health")
async def health_check(db: Annotated[AsyncSession, Depends(get_session)]):
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc
    return {"status": "healthy"}
