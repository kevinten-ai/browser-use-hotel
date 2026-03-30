-- ==========================================
-- 酒店比价 Web 版 — 数据库 Schema
-- ==========================================

-- 搜索任务表
create table if not exists tasks (
  id uuid primary key default gen_random_uuid(),
  hotel text not null,
  checkin date not null,
  checkout date not null,
  status text not null default 'pending'
    check (status in ('pending', 'running', 'completed', 'failed')),
  created_at timestamptz not null default now()
);

-- Agent 执行步骤日志（每步一行，含截图 URL）
create table if not exists step_logs (
  id bigint generated always as identity primary key,
  task_id uuid not null references tasks(id) on delete cascade,
  platform text not null,
  step_num int not null,
  goal text,
  screenshot_url text,
  created_at timestamptz not null default now()
);

-- 最终比价结果
create table if not exists results (
  id bigint generated always as identity primary key,
  task_id uuid not null references tasks(id) on delete cascade,
  platform text not null,
  hotel_name text,
  lowest_price numeric,
  room_type text,
  page_url text,
  error text,
  created_at timestamptz not null default now()
);

-- 索引：加速按 task_id 查询
create index idx_step_logs_task on step_logs(task_id);
create index idx_results_task on results(task_id);

-- RLS：允许匿名读写（demo 用途，生产环境应限制）
alter table tasks enable row level security;
alter table step_logs enable row level security;
alter table results enable row level security;

create policy "Allow all on tasks" on tasks for all using (true) with check (true);
create policy "Allow all on step_logs" on step_logs for all using (true) with check (true);
create policy "Allow all on results" on results for all using (true) with check (true);

-- Realtime
alter publication supabase_realtime add table step_logs;
alter publication supabase_realtime add table results;
alter publication supabase_realtime add table tasks;
