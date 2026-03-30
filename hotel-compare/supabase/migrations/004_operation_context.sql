-- 004_operation_context.sql
-- Store successful operation sequences for context injection in future searches

CREATE TABLE IF NOT EXISTS operation_contexts (
  id bigint generated always as identity primary key,
  platform text NOT NULL,
  hotel_pattern text,
  success boolean NOT NULL,
  steps_json jsonb NOT NULL,
  navigation_path text[],
  total_steps int,
  duration_seconds float,
  strategy_name text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_op_ctx_platform ON operation_contexts(platform);
CREATE INDEX IF NOT EXISTS idx_op_ctx_success ON operation_contexts(success);

ALTER TABLE operation_contexts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all on operation_contexts" ON operation_contexts FOR ALL USING (true) WITH CHECK (true);

ALTER PUBLICATION supabase_realtime ADD TABLE operation_contexts;
