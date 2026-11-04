# LLM Job Runner
This application accepts AI tasks, executes them asynchronously in background workers, and lets users track results, retry failures, and inspect token usage.

## Tasks types
The application was designed to make it easy to add support for new task types.

The current version supports two task types:
- Summarization: returns concise summary of a given text.
- Classification: classifies text into a fixed set of categories: "positive", "neutral", "negative", "mixed".

## Methods
### POST /api/v1/job Create Job
One of the key features is idempotent job submission. Therefore, each request must include an idempotency key in the request header.

Request JSON example:
```json
{
  "task_type": "classification",
  "input": {
    "text": "The delivery was late, but the product quality is good."
    }
}
```

Response JSON example:
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "queued",
  "task_type": "classification",
  "attempt_count": 1,
  "max_attempts": 5,
  "result_data": null,
  "error_message": null
}
```

### GET /api/v1/job/{job_id} Get Job
Retrieves information about a job by its ID.

Request example:
`http://localhost:8080/api/v1/job/3fa85f64-5717-4562-b3fc-2c963f66afa6`

Response JSON example:
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "succeeded",
  "task_type": "classification",
  "attempt_count": 1,
  "max_attempts": 5,
  "result_data": {
    "response": {
      "category": "mixed"
    },
    "usage": {
      "prompt_tokens": 93,
      "completion_tokens": 72
    }
  },
  "error_message": null
}
```

### POST /api/v1/job/{job_id}/retry Retry Job
Only jobs that have failed are eligible for retry.

Request example:
`http://localhost:8080/api/v1/job/51ce9fe2-c276-4a0e-bfb5-04f2aae0e9a0/retry`

Response JSON example:
```json
{
  "id": "51ce9fe2-c276-4a0e-bfb5-04f2aae0e9a0",
  "status": "queued",
  "task_type": "summarization",
  "attempt_count": 3,
  "max_attempts": 5,
  "result_data": null,
  "error_message": null
}
```

## Tech stack
- Python: Main programming language.
- FastAPI: For quickly building API endpoints.
- PostgreSQL: Relational database.
- SQLAlchemy: ORM for database operations.
- Pydantic: Data validation and serialization.
- RabbitMQ: Message broker for asynchronous communication between the API and background workers.
- aio-pika: Python library for interacting with RabbitMQ.
- OpenAI API: For making LLM calls.
- Docker: For containerization and deployment.
- Pytest: For automated testing.

## Project directory structure
- `app\`. Contains the application's main functionality.
- `migrations\`. Contains SQL scripts for database initialization.
- `tests\`. Contains automated tests.
- `app\core\`. Application configuration and shared utilities, including settings, LLM client, and RabbitMQ setup.
- `app\db\`. Database engine configuration and SQLAlchemy models.
- `app\routers\`. FastAPI API endpoints.
- `app\schemas\`. Pydantic schemas.
- `app\worker\`. RabbitMQ consumer and background worker implementation.
- `app\main.py`. Application entry point.

## Requirments
- OpenAI API key.
- Python 3.13+.
- Docker 29.4.3+.
- Docker Compose v5.1.3+.

## Configuration
Create a `.env` file in the project root directory with the following variables:
| Variable | Description | Example |
|---|---|---|
|DB_URL|Database connection URL|postgresql+asyncpg://user:password@localhost:5432/test_db|
|DB_NAME|Database name|test_db|
|DB_USER|Database username|user|
|DB_PASSWORD|Database password|password|
|RABBITMQ_USER|RabbitMQ username|user|
|RABBITMQ_PASSWORD|RabbitMQ password|password|
|LLM_API_KEY|OpenAI API key|valid-key|
|LLM_BASE_URL|OpenAI API base URL|https://example.com/v1|
|LLM_MODEL|LLM model name|model-name|

To run the **automated tests**, you must also create a `.env.test` file in the project root directory. It should contain the same variables, using placeholder values for all variables except `DB_URL`, which should point to a separate test database.

## Deploy with Docker
Build and start the application using Docker Compose:
`docker compose up -d --build`

## Run automated tests
`pytest -v`