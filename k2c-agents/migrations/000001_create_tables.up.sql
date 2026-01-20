CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS data_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id text NOT NULL,
    captured_at timestamptz NOT NULL,
    received_at timestamptz NOT NULL,
    content_type text,
    size_bytes integer,
    sha256 text,
    object_key text NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    processed_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_data_events_received_at ON data_events (received_at);

CREATE TABLE IF NOT EXISTS features (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id uuid NOT NULL REFERENCES data_events(id) ON DELETE CASCADE,
    features jsonb NOT NULL,
    extracted_at timestamptz NOT NULL,
    model text
);

CREATE INDEX IF NOT EXISTS idx_features_event_id ON features (event_id);

CREATE TABLE IF NOT EXISTS evaluations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_id uuid NOT NULL REFERENCES features(id) ON DELETE CASCADE,
    evaluation jsonb NOT NULL,
    goal text NOT NULL,
    evaluated_at timestamptz NOT NULL,
    model text
);

CREATE INDEX IF NOT EXISTS idx_evaluations_feature_id ON evaluations (feature_id);

CREATE TABLE IF NOT EXISTS config_store (
    key text PRIMARY KEY,
    value jsonb NOT NULL,
    updated_at timestamptz NOT NULL
);
