-- 005_dual_engine.sql
-- Add engine tracking to support dual-engine comparison (browser-use vs page-agent)

ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS engine text DEFAULT 'browser-use'
    CHECK (engine IN ('browser-use', 'page-agent', 'dual'));

ALTER TABLE step_logs
  ADD COLUMN IF NOT EXISTS engine text DEFAULT 'browser-use';

ALTER TABLE results
  ADD COLUMN IF NOT EXISTS engine text DEFAULT 'browser-use',
  ADD COLUMN IF NOT EXISTS duration_seconds float;
