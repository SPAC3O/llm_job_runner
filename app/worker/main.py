import asyncio
import logging
import aio_pika

from . import consumer
from core import settings, OpenAIClient


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    connection = await aio_pika.connect_robust(
        "amqp://"
        + settings.rabbitmq.user
        + ":"
        + settings.rabbitmq.password
        + "@"
        + settings.rabbitmq.host
        + ":"
        + str(settings.rabbitmq.port)
        + "/"
    )

    llm_client = OpenAIClient()

    try:
        logger.info("Starting LLM worker")
        await consumer.consume(
            connection=connection,
            queue=settings.queue.llm_jobs_queue,
            llm_client=llm_client,
        )
    finally:
        logger.info("Closing worker connections")
        await llm_client.close()
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
