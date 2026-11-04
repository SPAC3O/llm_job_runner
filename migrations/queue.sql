CREATE EXTENSION IF NOT EXISTS moddatetime;


CREATE TABLE IF NOT EXISTS job (
    id                  UUID PRIMARY KEY    NOT NULL DEFAULT gen_random_uuid(),
    created_at          TIMESTAMPTZ         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMPTZ         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    task_type           VARCHAR(15)         NOT NULL,
    status              VARCHAR(10)         NOT NULL,
    input_data          JSONB               NOT NULL,
    result_data         JSONB               NULL,
    error_message       TEXT                NULL,
    idempotency_key     VARCHAR(255)        NOT NULL,
    attempt_count       INTEGER             NOT NULL,
    max_attempts        INTEGER             NOT NULL,
    prompt_tokens       INTEGER             NULL,
    completion_tokens   INTEGER             NULL
);

DROP TRIGGER IF EXISTS trg_upd_job_updated_at ON job;
CREATE TRIGGER trg_upd_job_updated_at
BEFORE UPDATE ON job
FOR EACH ROW
EXECUTE PROCEDURE moddatetime (updated_at);

ALTER TABLE job
    DROP CONSTRAINT IF EXISTS uq_idempotency_key,
    ADD CONSTRAINT uq_idempotency_key UNIQUE (idempotency_key);


CREATE TABLE IF NOT EXISTS job_attempt(
    id                  UUID PRIMARY KEY    NOT NULL DEFAULT gen_random_uuid(),
    created_at          TIMESTAMPTZ         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMPTZ         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    job_id              UUID REFERENCES job(id) NOT NULL,
    attempt_number      INTEGER             NOT NULL,
    status              VARCHAR(10)         NOT NULL,
    prompt_tokens       INTEGER             NULL,
    completion_tokens   INTEGER             NULL,
    latency_ms          INTEGER             NULL,
    error_message       TEXT                NULL,
    started_at          TIMESTAMPTZ         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at         TIMESTAMPTZ         NULL
);

DROP TRIGGER IF EXISTS trg_upd_job_attempt_updated_at ON job_attempt;
CREATE TRIGGER trg_upd_job_attempt_updated_at
BEFORE UPDATE ON job_attempt
FOR EACH ROW
EXECUTE PROCEDURE moddatetime (updated_at);

ALTER TABLE job_attempt
    DROP CONSTRAINT IF EXISTS uq_job_id_attempt_number,
    ADD CONSTRAINT uq_job_id_attempt_number UNIQUE (job_id, attempt_number);