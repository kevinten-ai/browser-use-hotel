# browser-use-hotel

AI Browser Agent 自动操控浏览器，实时搜索携程、去哪儿、同程三大酒店平台，截图直播比价。

**Live Demo** &rarr; [hotel.rxcloud.group](https://hotel.rxcloud.group)

---

## Demo

### 1. 输入酒店名称，点击"开始比价"

<img src="hotel-compare/docs/screenshot-search.png" width="720" />

### 2. CRT 终端风格启动动画 — 三个 Agent 同时启动

<img src="hotel-compare/docs/screenshot-boot.png" width="720" />

### 3. Agent 操控浏览器搜索，截图实时推送

<img src="hotel-compare/docs/screenshot-results.png" width="720" />

---

## How It Works

```
用户输入酒店 → 创建任务 → Worker 轮询领取 → 启动 3 个 browser-use Agent
                                              ↓
                                    每个 Agent 控制一个 Chromium
                                    → 打开携程/去哪儿/同程
                                    → 搜索酒店、设置日期
                                    → 提取最低价格和房型
                                              ↓
                              截图 + 步骤日志 → Supabase Storage & DB
                                              ↓
                              前端 3 秒轮询 → 实时展示截图和结果
```

## Tech Stack

| Layer | Technology | Deployment |
|-------|-----------|------------|
| **Frontend** | Next.js 16, Tailwind CSS | [Vercel](https://vercel.com) |
| **Database** | Supabase (PostgreSQL + Storage) | [Supabase](https://supabase.com) |
| **Worker** | Python, [browser-use](https://github.com/browser-use/browser-use), Playwright | [Railway](https://railway.com) |
| **LLM** | GLM-4-Plus (OpenAI-compatible API) | [ZhiPu AI](https://open.bigmodel.cn) |

## Key Features

- **CRT Boot Animation** — 终端风格开机动画，显示 Agent 初始化进度
- **Screenshot Streaming** — Chromium 截图实时上传到 Supabase Storage，前端每 3 秒拉取展示
- **Price Validation** — 价格范围过滤（¥30–50,000），防止将年份、日期误解析为价格
- **Error Isolation** — 单平台失败不影响其他平台，每个 Agent 独立运行
- **Structured Output** — Pydantic BaseModel 解析 Agent 输出，JSON 正则兜底

## Architecture

```
hotel-compare/
├── web/                        # Next.js frontend
│   ├── app/page.tsx            # 主页（轮询 + 展示）
│   ├── components/
│   │   ├── SearchForm.tsx      # 搜索表单 → 创建 task
│   │   ├── PlatformCard.tsx    # 平台卡片（截图 + 状态）
│   │   ├── BootAnimation.tsx   # CRT 启动动画
│   │   └── ComparisonTable.tsx # 比价结果表
│   └── lib/supabase.ts         # Supabase client
│
├── browser-use-version/        # Python worker
│   ├── worker.py               # 轮询任务队列
│   ├── hotel_compare.py        # 3 平台搜索逻辑 + prompt
│   ├── supabase_client.py      # DB/Storage 操作
│   └── Dockerfile              # Railway 部署
│
└── supabase/                   # 数据库 schema
    └── migrations/
```

## Quick Start

### Frontend

```bash
cd hotel-compare/web
npm install
# Set env vars
echo 'NEXT_PUBLIC_SUPABASE_URL=your_url' > .env.local
echo 'NEXT_PUBLIC_SUPABASE_ANON_KEY=your_key' >> .env.local
npm run dev
```

### Worker

```bash
cd hotel-compare/browser-use-version
uv sync
uv run playwright install chromium
# Set env vars
cp .env.example .env
# Edit .env: SUPABASE_URL, SUPABASE_KEY, OPENAI_BASE_URL, OPENAI_MODEL
uv run python worker.py
```

### Supabase Tables

```sql
-- tasks: 搜索任务队列
CREATE TABLE tasks (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  hotel TEXT NOT NULL,
  checkin DATE NOT NULL,
  checkout DATE NOT NULL,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending','running','completed','failed')),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- step_logs: Agent 步骤日志 + 截图
CREATE TABLE step_logs (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  task_id UUID REFERENCES tasks(id),
  platform TEXT NOT NULL,
  step_num INT NOT NULL,
  goal TEXT,
  screenshot_url TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- results: 比价结果
CREATE TABLE results (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  task_id UUID REFERENCES tasks(id),
  platform TEXT NOT NULL,
  hotel_name TEXT,
  lowest_price NUMERIC,
  room_type TEXT,
  page_url TEXT,
  error TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

## Two Engine Comparison

本项目用两种 Browser Agent 方案实现同一个任务：

| | browser-use（服务端） | page-agent（客户端） |
|---|---|---|
| **运行时** | Python + Playwright（headless） | Chrome Extension（用户浏览器） |
| **LLM** | GLM-4-Plus via API | OpenAI API |
| **部署** | Railway Docker | 本地 Chrome |
| **可观测性** | 截图 + step_logs | Console logs |
| **反爬** | headless 检测风险 | 真实用户浏览器 |
| **代码位置** | `browser-use-version/` | `page-agent-version/` |

## License

MIT
