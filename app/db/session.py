from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core import settings

async_engine = create_async_engine(url=settings.database.url)

async_session_local = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session():
    async with async_session_local() as session:
        yield session
