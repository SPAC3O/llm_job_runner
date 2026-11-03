import aio_pika
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rabbitmq")


async def publish_message(
    connection: aio_pika.RobustConnection, msg: str, queue: str
) -> None:
    channel = await connection.channel()

    async with channel:
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=msg.encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=queue,
        )
        logger.info(f"Sent message to queue: {msg}")
