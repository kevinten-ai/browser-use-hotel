-- 003_retry_tracking.sql
-- Add strategy tracking columns to results table

ALTER TABLE results
  ADD COLUMN IF NOT EXISTS strategy_name text,
  ADD COLUMN IF NOT EXISTS attempt_number int DEFAULT 1;
