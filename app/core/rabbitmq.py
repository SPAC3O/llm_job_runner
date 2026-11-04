import aio_pika
from aio_pika.abc import AbstractRobustConnection

from core import settings

QUEUES = (settings.queue.llm_jobs_queue)


async def connect() -> AbstractRobustConnection:
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

    async with connection.channel() as channel:
        for queue_name in QUEUES:
            await channel.declare_queue(
                queue_name,
                durable=True,
            )

    return connection
