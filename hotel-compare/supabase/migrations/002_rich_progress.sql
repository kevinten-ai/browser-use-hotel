-- 002_rich_progress.sql
-- Expand step_logs to store full Agent reasoning data (thinking, evaluation, memory, actions, plan, url)

ALTER TABLE step_logs
  ADD COLUMN IF NOT EXISTS thinking text,
  ADD COLUMN IF NOT EXISTS evaluation text,
  ADD COLUMN IF NOT EXISTS memory text,
  ADD COLUMN IF NOT EXISTS actions jsonb,
  ADD COLUMN IF NOT EXISTS plan jsonb,
  ADD COLUMN IF NOT EXISTS url text;
