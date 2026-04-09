# Hotel Compare Web Deployment Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the hotel comparison tool as a zero-install web app where users visit a URL, trigger a search, and watch browser screenshots stream in real-time.

**Architecture:** Three-tier — Vercel (Next.js frontend) + Supabase (DB + Realtime + Storage) + Railway (Python worker with browser-use + headless Chromium). User submits search via frontend → task row inserted into Supabase → worker picks it up, runs browser-use agents, uploads screenshots per step → frontend subscribes to Supabase Realtime and renders a live screenshot feed → final results displayed as comparison table.

**Tech Stack:** Next.js 14 (App Router), Supabase (PostgreSQL + Realtime + Storage), Python 3.11 + browser-use + supabase-py, Railway (worker host)

---

## File Structure

```
hotel-compare/
├── browser-use-version/          # EXISTING — Python worker
│   ├── hotel_compare.py          # MODIFY — add headless mode, screenshot capture
│   ├── worker.py                 # CREATE — Supabase task poller + runner
│   ├── supabase_client.py        # CREATE — Supabase client wrapper
│   ├── pyproject.toml            # MODIFY — add supabase dependency
│   ├── Dockerfile                # CREATE — for Railway deployment
│   └── .env.example              # MODIFY — add Supabase env vars
│
├── web/                          # CREATE — Next.js frontend
│   ├── package.json
│   ├── next.config.js
│   ├── .env.local.example
│   ├── app/
│   │   ├── layout.tsx            # Root layout with fonts + metadata
│   │   ├── page.tsx              # Main page — search form + results
│   │   └── globals.css           # Tailwind + custom styles
│   ├── components/
│   │   ├── SearchForm.tsx        # Hotel name + date inputs + submit
│   │   ├── PlatformCard.tsx      # Single platform: screenshot + status + price
│   │   └── ComparisonTable.tsx   # Final results comparison
│   ├── lib/
│   │   ├── supabase.ts           # Supabase browser client
│   │   └── types.ts              # Shared TypeScript types
│   └── tailwind.config.ts
│
└── supabase/
    └── migrations/
        └── 001_init.sql          # CREATE — all tables + RLS + storage
```

---

## Chunk 1: Supabase Schema & Storage

### Task 1: Create Supabase migration SQL

**Files:**
- Create: `hotel-compare/supabase/migrations/001_init.sql`

- [ ] **Step 1: Write the migration SQL**

```sql
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
```

- [ ] **Step 2: Apply migration via Supabase Dashboard or CLI**

Go to Supabase Dashboard → SQL Editor → paste and run the SQL above.

Or via CLI:
```bash
supabase db push
```

- [ ] **Step 3: Create Storage bucket for screenshots**

In Supabase Dashboard → Storage → Create bucket:
- Name: `screenshots`
- Public: Yes (so frontend can load images directly)

Or via SQL:
```sql
insert into storage.buckets (id, name, public) values ('screenshots', 'screenshots', true);

-- Allow public read + authenticated upload
create policy "Public read screenshots" on storage.objects
  for select using (bucket_id = 'screenshots');
create policy "Allow upload screenshots" on storage.objects
  for insert with check (bucket_id = 'screenshots');
```

- [ ] **Step 4: Enable Realtime on step_logs and results tables**

In Supabase Dashboard → Database → Replication → Enable for:
- `step_logs` (INSERT)
- `results` (INSERT)
- `tasks` (UPDATE)

Or via SQL:
```sql
alter publication supabase_realtime add table step_logs;
alter publication supabase_realtime add table results;
alter publication supabase_realtime add table tasks;
```

- [ ] **Step 5: Verify — check tables exist**

```sql
select table_name from information_schema.tables
where table_schema = 'public' and table_name in ('tasks', 'step_logs', 'results');
```

Expected: 3 rows.

---

## Chunk 2: Python Worker (Supabase Integration)

### Task 2: Add supabase dependency

**Files:**
- Modify: `hotel-compare/browser-use-version/pyproject.toml`

- [ ] **Step 1: Add supabase to dependencies**

Add `"supabase>=2.0.0"` to the dependencies list in pyproject.toml.

- [ ] **Step 2: Update .env.example**

Append:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

- [ ] **Step 3: Run uv sync**

```bash
cd hotel-compare/browser-use-version && uv sync
```

### Task 3: Create Supabase client wrapper

**Files:**
- Create: `hotel-compare/browser-use-version/supabase_client.py`

- [ ] **Step 1: Write supabase_client.py**

```python
"""Supabase client — 封装数据库和存储操作"""

import os
import base64
from supabase import create_client

_client = None

def get_client():
    global _client
    if _client is None:
        _client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_KEY"],
        )
    return _client

def create_task(hotel: str, checkin: str, checkout: str) -> str:
    """创建搜索任务，返回 task_id"""
    resp = get_client().table("tasks").insert({
        "hotel": hotel,
        "checkin": checkin,
        "checkout": checkout,
        "status": "pending",
    }).execute()
    return resp.data[0]["id"]

def update_task_status(task_id: str, status: str):
    get_client().table("tasks").update({"status": status}).eq("id", task_id).execute()

def fetch_pending_task():
    """获取一个 pending 任务并标记为 running（原子操作）"""
    resp = (
        get_client()
        .table("tasks")
        .select("*")
        .eq("status", "pending")
        .order("created_at")
        .limit(1)
        .execute()
    )
    if not resp.data:
        return None
    task = resp.data[0]
    # 标记为 running（简单实现，生产环境应用 RPC 做原子锁）
    update_task_status(task["id"], "running")
    return task

def upload_screenshot(task_id: str, platform: str, step_num: int, screenshot_b64: str) -> str:
    """上传 base64 截图到 Supabase Storage，返回公开 URL"""
    path = f"{task_id}/{platform}_{step_num}.png"
    file_bytes = base64.b64decode(screenshot_b64)
    get_client().storage.from_("screenshots").upload(
        path, file_bytes, {"content-type": "image/png"}
    )
    return get_client().storage.from_("screenshots").get_public_url(path)

def insert_step_log(task_id: str, platform: str, step_num: int, goal: str, screenshot_url: str):
    get_client().table("step_logs").insert({
        "task_id": task_id,
        "platform": platform,
        "step_num": step_num,
        "goal": goal,
        "screenshot_url": screenshot_url,
    }).execute()

def insert_result(task_id: str, platform: str, hotel_name: str = None,
                  lowest_price: float = None, room_type: str = None,
                  page_url: str = None, error: str = None):
    get_client().table("results").insert({
        "task_id": task_id,
        "platform": platform,
        "hotel_name": hotel_name,
        "lowest_price": lowest_price,
        "room_type": room_type,
        "page_url": page_url,
        "error": error,
    }).execute()
```

- [ ] **Step 2: Verify — import test**

```bash
cd hotel-compare/browser-use-version
uv run python -c "from supabase_client import get_client; print('OK')"
```

### Task 4: Modify hotel_compare.py for screenshot streaming

**Files:**
- Modify: `hotel-compare/browser-use-version/hotel_compare.py`

- [ ] **Step 1: Add screenshot-aware step callback factory**

Add a new callback factory function that uploads screenshots to Supabase:

```python
def make_streaming_callback(platform_name: str, task_id: str):
    """创建步骤回调：截图上传 Supabase + 写入 step_logs"""
    from supabase_client import upload_screenshot, insert_step_log

    async def on_step(browser_state, agent_output, step_num):
        goal = (agent_output.current_state.next_goal
                if agent_output and agent_output.current_state else "")
        screenshot_url = ""
        if browser_state and browser_state.screenshot:
            try:
                screenshot_url = upload_screenshot(
                    task_id, platform_name, step_num, browser_state.screenshot
                )
            except Exception as e:
                print(f"  [{platform_name}] Screenshot upload failed: {e}")
        insert_step_log(task_id, platform_name, step_num, goal, screenshot_url)
        print(f"  [{platform_name}] Step {step_num}: {goal}")

    return on_step
```

- [ ] **Step 2: Add task_id parameter to search functions**

Modify each search function signature to accept optional `task_id`:

```python
async def search_ctrip(hotel, checkin, checkout, logs, task_id=None):
```

When `task_id` is provided, use `make_streaming_callback` instead of `make_step_callback`:

```python
    callback = (make_streaming_callback("携程", task_id) if task_id
                else make_step_callback("携程", logs))
```

Apply the same change to `search_qunar` and `search_tongcheng`.

- [ ] **Step 3: Switch to headless mode when task_id is present**

```python
    browser = BrowserSession(headless=(task_id is not None))
```

This allows: local dev = visible browser, deployed worker = headless.

- [ ] **Step 4: Verify — existing CLI still works**

```bash
uv run python hotel_compare.py --hotel "北京国贸大酒店" --checkin 2026-04-15 --checkout 2026-04-17
```

Should work as before (no task_id → uses original callback, headless=False).

### Task 5: Create worker.py (task poller)

**Files:**
- Create: `hotel-compare/browser-use-version/worker.py`

- [ ] **Step 1: Write worker.py**

```python
"""Worker — 轮询 Supabase 任务队列，执行 browser-use 搜索"""

import asyncio
import time
import os
from dotenv import load_dotenv

load_dotenv()

from supabase_client import fetch_pending_task, update_task_status, insert_result
from hotel_compare import search_ctrip, search_qunar, search_tongcheng


async def process_task(task: dict):
    """处理一个搜索任务"""
    task_id = task["id"]
    hotel = task["hotel"]
    checkin = task["checkin"]
    checkout = task["checkout"]
    print(f"\n{'='*50}")
    print(f"Processing: {hotel} | {checkin} → {checkout}")
    print(f"Task ID: {task_id}")

    platforms = [
        ("携程", search_ctrip),
        ("去哪儿", search_qunar),
        ("同程", search_tongcheng),
    ]

    logs = []  # still needed for function signature
    for name, search_fn in platforms:
        print(f"\n  Searching {name}...")
        try:
            result = await search_fn(hotel, checkin, checkout, logs, task_id=task_id)
            if result:
                insert_result(
                    task_id, name,
                    hotel_name=result.hotel_name,
                    lowest_price=result.lowest_price,
                    room_type=result.room_type,
                    page_url=result.url,
                )
                print(f"  {name}: ¥{result.lowest_price:.0f} {result.room_type}")
            else:
                insert_result(task_id, name, error="Search returned no result")
                print(f"  {name}: No result")
        except Exception as e:
            insert_result(task_id, name, error=str(e))
            print(f"  {name}: Error - {e}")

    update_task_status(task_id, "completed")
    print(f"\nTask {task_id} completed.")


def poll_loop():
    """主循环：每 5 秒检查一次新任务"""
    print("Worker started. Polling for tasks...")
    while True:
        task = fetch_pending_task()
        if task:
            asyncio.run(process_task(task))
        else:
            time.sleep(5)


if __name__ == "__main__":
    poll_loop()
```

- [ ] **Step 2: Verify — worker starts without error**

```bash
uv run python worker.py
```

Expected: prints "Worker started. Polling for tasks..." and polls.

- [ ] **Step 3: Commit worker + supabase integration**

```bash
git add worker.py supabase_client.py
git commit -m "feat: add Supabase worker for cloud deployment"
```

### Task 6: Create Dockerfile for Railway

**Files:**
- Create: `hotel-compare/browser-use-version/Dockerfile`

- [ ] **Step 1: Write Dockerfile**

```dockerfile
FROM python:3.11-slim

# Install Chromium dependencies
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates fonts-wqy-zenhei \
    libnss3 libatk-bridge2.0-0 libdrm2 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libasound2 libpango-1.0-0 \
    libcairo2 libcups2 libxss1 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .

# Install Playwright browsers
RUN uv run playwright install chromium

CMD ["uv", "run", "python", "worker.py"]
```

- [ ] **Step 2: Verify — Docker builds**

```bash
cd hotel-compare/browser-use-version
docker build -t hotel-worker .
```

- [ ] **Step 3: Commit**

```bash
git add Dockerfile
git commit -m "feat: add Dockerfile for Railway deployment"
```

---

## Chunk 3: Next.js Frontend

### Task 7: Initialize Next.js project

**Files:**
- Create: `hotel-compare/web/` (entire directory)

- [ ] **Step 1: Create Next.js app**

```bash
cd hotel-compare
npx create-next-app@latest web --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*"
```

- [ ] **Step 2: Install Supabase client**

```bash
cd hotel-compare/web
npm install @supabase/supabase-js
```

- [ ] **Step 3: Create .env.local.example**

```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

- [ ] **Step 4: Commit scaffold**

```bash
git add web/
git commit -m "feat: scaffold Next.js frontend"
```

### Task 8: Create Supabase client + types

**Files:**
- Create: `hotel-compare/web/lib/supabase.ts`
- Create: `hotel-compare/web/lib/types.ts`

- [ ] **Step 1: Write lib/types.ts**

```typescript
export interface Task {
  id: string;
  hotel: string;
  checkin: string;
  checkout: string;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;
}

export interface StepLog {
  id: number;
  task_id: string;
  platform: string;
  step_num: number;
  goal: string;
  screenshot_url: string;
  created_at: string;
}

export interface Result {
  id: number;
  task_id: string;
  platform: string;
  hotel_name: string | null;
  lowest_price: number | null;
  room_type: string | null;
  page_url: string | null;
  error: string | null;
}
```

- [ ] **Step 2: Write lib/supabase.ts**

```typescript
import { createClient } from "@supabase/supabase-js";

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);
```

### Task 9: Build SearchForm component

**Files:**
- Create: `hotel-compare/web/components/SearchForm.tsx`

- [ ] **Step 1: Write SearchForm.tsx**

```tsx
"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";

interface Props {
  onTaskCreated: (taskId: string) => void;
  disabled?: boolean;
}

export default function SearchForm({ onTaskCreated, disabled }: Props) {
  const [hotel, setHotel] = useState("北京国贸大酒店");
  const [checkin, setCheckin] = useState("2026-04-15");
  const [checkout, setCheckout] = useState("2026-04-17");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    const { data, error } = await supabase
      .from("tasks")
      .insert({ hotel, checkin, checkout })
      .select("id")
      .single();
    setLoading(false);
    if (data) onTaskCreated(data.id);
    if (error) alert("Failed to create task: " + error.message);
  }

  const isDisabled = disabled || loading;

  return (
    <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 items-end">
      <div className="flex-1">
        <label className="block text-sm font-medium text-gray-700 mb-1">酒店名称</label>
        <input
          type="text"
          value={hotel}
          onChange={(e) => setHotel(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="输入酒店名称"
          required
          disabled={isDisabled}
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">入住</label>
        <input
          type="date"
          value={checkin}
          onChange={(e) => setCheckin(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          required
          disabled={isDisabled}
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">离店</label>
        <input
          type="date"
          value={checkout}
          onChange={(e) => setCheckout(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          required
          disabled={isDisabled}
        />
      </div>
      <button
        type="submit"
        disabled={isDisabled}
        className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
      >
        {loading ? "提交中..." : "开始比价"}
      </button>
    </form>
  );
}
```

### Task 10: Build PlatformCard component (screenshot stream)

**Files:**
- Create: `hotel-compare/web/components/PlatformCard.tsx`

- [ ] **Step 1: Write PlatformCard.tsx**

```tsx
"use client";

import { StepLog, Result } from "@/lib/types";

interface Props {
  platform: string;
  steps: StepLog[];
  result?: Result | null;
}

export default function PlatformCard({ platform, steps, result }: Props) {
  const latestStep = steps[steps.length - 1];
  const isSearching = steps.length > 0 && !result;
  const hasError = result?.error;

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
      {/* Header */}
      <div className="px-4 py-3 bg-gray-50 border-b flex items-center justify-between">
        <h3 className="font-semibold text-lg">{platform}</h3>
        <span className="text-sm">
          {!steps.length && !result && "等待中..."}
          {isSearching && `Step ${latestStep.step_num}`}
          {result && !hasError && `¥${result.lowest_price}`}
          {hasError && "失败"}
        </span>
      </div>

      {/* Screenshot area */}
      <div className="aspect-video bg-gray-100 relative overflow-hidden">
        {latestStep?.screenshot_url ? (
          <img
            src={latestStep.screenshot_url}
            alt={`${platform} Step ${latestStep.step_num}`}
            className="w-full h-full object-cover object-top"
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400">
            {isSearching ? "截图加载中..." : "等待搜索开始"}
          </div>
        )}
        {isSearching && (
          <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-xs px-3 py-1.5 truncate">
            {latestStep.goal}
          </div>
        )}
      </div>

      {/* Result footer */}
      {result && !hasError && (
        <div className="px-4 py-3 bg-green-50 border-t">
          <p className="font-bold text-green-800 text-xl">¥{result.lowest_price}</p>
          <p className="text-sm text-gray-600">{result.room_type}</p>
          <p className="text-xs text-gray-400 truncate">{result.hotel_name}</p>
        </div>
      )}
      {hasError && (
        <div className="px-4 py-3 bg-red-50 border-t">
          <p className="text-sm text-red-600">搜索失败: {result.error}</p>
        </div>
      )}
    </div>
  );
}
```

### Task 11: Build ComparisonTable component

**Files:**
- Create: `hotel-compare/web/components/ComparisonTable.tsx`

- [ ] **Step 1: Write ComparisonTable.tsx**

```tsx
import { Result } from "@/lib/types";

interface Props {
  results: Result[];
}

export default function ComparisonTable({ results }: Props) {
  const valid = results
    .filter((r) => r.lowest_price != null)
    .sort((a, b) => a.lowest_price! - b.lowest_price!);

  if (valid.length === 0) return null;

  const cheapest = valid[0];

  return (
    <div className="mt-8">
      <h2 className="text-xl font-bold mb-4">比价结果</h2>
      <div className="overflow-hidden rounded-xl border border-gray-200">
        <table className="w-full text-left">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-sm font-medium text-gray-500">平台</th>
              <th className="px-4 py-3 text-sm font-medium text-gray-500">最低价</th>
              <th className="px-4 py-3 text-sm font-medium text-gray-500">房型</th>
              <th className="px-4 py-3 text-sm font-medium text-gray-500">酒店名</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {valid.map((r) => (
              <tr
                key={r.platform}
                className={r.id === cheapest.id ? "bg-green-50" : ""}
              >
                <td className="px-4 py-3 font-medium">
                  {r.id === cheapest.id && "🏆 "}{r.platform}
                </td>
                <td className="px-4 py-3 font-bold text-lg">¥{r.lowest_price}</td>
                <td className="px-4 py-3 text-gray-600">{r.room_type || "-"}</td>
                <td className="px-4 py-3 text-gray-600 text-sm">{r.hotel_name || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {valid.length >= 2 && (
        <p className="mt-3 text-green-700 font-medium">
          最低价: {cheapest.platform} ¥{cheapest.lowest_price}
          (比最高价低 ¥{valid[valid.length - 1].lowest_price! - cheapest.lowest_price!})
        </p>
      )}
    </div>
  );
}
```

### Task 12: Build main page with Realtime subscription

**Files:**
- Modify: `hotel-compare/web/app/page.tsx`

- [ ] **Step 1: Write the main page**

```tsx
"use client";

import { useEffect, useState, useCallback } from "react";
import { supabase } from "@/lib/supabase";
import { StepLog, Result } from "@/lib/types";
import SearchForm from "@/components/SearchForm";
import PlatformCard from "@/components/PlatformCard";
import ComparisonTable from "@/components/ComparisonTable";

const PLATFORMS = ["携程", "去哪儿", "同程"];

export default function Home() {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [steps, setSteps] = useState<StepLog[]>([]);
  const [results, setResults] = useState<Result[]>([]);
  const [taskStatus, setTaskStatus] = useState<string>("idle");

  const handleTaskCreated = useCallback((id: string) => {
    setTaskId(id);
    setSteps([]);
    setResults([]);
    setTaskStatus("running");
  }, []);

  // Subscribe to Realtime updates when taskId changes
  useEffect(() => {
    if (!taskId) return;

    // Subscribe to new step_logs for this task
    const stepsChannel = supabase
      .channel(`steps-${taskId}`)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "step_logs",
          filter: `task_id=eq.${taskId}`,
        },
        (payload) => {
          setSteps((prev) => [...prev, payload.new as StepLog]);
        }
      )
      .subscribe();

    // Subscribe to results for this task
    const resultsChannel = supabase
      .channel(`results-${taskId}`)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "results",
          filter: `task_id=eq.${taskId}`,
        },
        (payload) => {
          setResults((prev) => [...prev, payload.new as Result]);
        }
      )
      .subscribe();

    // Subscribe to task status
    const taskChannel = supabase
      .channel(`task-${taskId}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "tasks",
          filter: `id=eq.${taskId}`,
        },
        (payload) => {
          setTaskStatus((payload.new as { status: string }).status);
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(stepsChannel);
      supabase.removeChannel(resultsChannel);
      supabase.removeChannel(taskChannel);
    };
  }, [taskId]);

  const isRunning = taskStatus === "running";

  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-2">酒店跨平台比价</h1>
      <p className="text-gray-500 mb-6">
        基于 browser-use Agent — AI 自动操控浏览器搜索三大平台，实时截图直播
      </p>

      <SearchForm onTaskCreated={handleTaskCreated} disabled={isRunning} />

      {taskId && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
            {PLATFORMS.map((p) => (
              <PlatformCard
                key={p}
                platform={p}
                steps={steps.filter((s) => s.platform === p)}
                result={results.find((r) => r.platform === p)}
              />
            ))}
          </div>

          {taskStatus === "completed" && <ComparisonTable results={results} />}

          {isRunning && (
            <p className="mt-4 text-center text-gray-400 animate-pulse">
              Agent 正在搜索中... 截图实时更新
            </p>
          )}
        </>
      )}
    </main>
  );
}
```

- [ ] **Step 2: Update app/layout.tsx**

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "酒店跨平台比价 — browser-use Agent",
  description: "AI 自动操控浏览器，实时比较三大酒店平台价格",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="bg-gray-50 min-h-screen">{children}</body>
    </html>
  );
}
```

- [ ] **Step 3: Verify — dev server starts**

```bash
cd hotel-compare/web
cp .env.local.example .env.local  # fill in real values
npm run dev
```

Open http://localhost:3000 — should see the search form.

- [ ] **Step 4: Commit frontend**

```bash
git add web/
git commit -m "feat: Next.js frontend with Supabase Realtime screenshot streaming"
```

---

## Chunk 4: Deployment

### Task 13: Deploy frontend to Vercel

- [ ] **Step 1: Push to GitHub**

```bash
git push origin main
```

- [ ] **Step 2: Connect to Vercel**

1. Go to vercel.com → Import Project → Select repo
2. Set Root Directory: `hotel-compare/web`
3. Add Environment Variables:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
4. Deploy

- [ ] **Step 3: Verify — visit Vercel URL, search form renders**

### Task 14: Deploy worker to Railway

- [ ] **Step 1: Create Railway project**

1. Go to railway.app → New Project → Deploy from GitHub
2. Set Root Directory: `hotel-compare/browser-use-version`
3. Railway will auto-detect the Dockerfile
4. Add Environment Variables:
   - `OPENAI_API_KEY`
   - `OPENAI_BASE_URL`
   - `OPENAI_MODEL`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`

- [ ] **Step 2: Verify — check Railway logs**

Should see "Worker started. Polling for tasks..."

### Task 15: End-to-end test

- [ ] **Step 1: Visit Vercel URL → enter hotel → click 比价**
- [ ] **Step 2: Watch screenshots appear in real-time in the 3 platform cards**
- [ ] **Step 3: Wait for completion → verify comparison table shows results**
