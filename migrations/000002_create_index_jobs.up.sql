CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS index_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_request jsonb NOT NULL,
    payload jsonb NOT NULL,
    status text NOT NULL,
    enqueued_at timestamptz NOT NULL,
    processed_at timestamptz,
    last_error text
);

CREATE INDEX IF NOT EXISTS idx_index_jobs_status ON index_jobs (status);
