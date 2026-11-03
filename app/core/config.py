from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Union


class Database(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="db_",
        extra="ignore",
    )

    url: str


class RabbitMQ(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="rabbitmq_",
        extra="ignore",
    )

    user: str
    password: str
    host: str = "rabbitmq"
    port: Union[int, str] = 5672


class Queue(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="rabbitmq_",
        extra="ignore",
    )

    llm_jobs_queue: str = "llm_jobs"


class LLM(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="llm_",
        extra="ignore",
    )

    api_key: str
    base_url: str
    model: str


class Settings:
    database: Database = Database()
    rabbitmq: RabbitMQ = RabbitMQ()
    queue: Queue = Queue()
    llm: LLM = LLM()


settings = Settings()
