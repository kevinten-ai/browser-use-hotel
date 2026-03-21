# 酒店跨平台比价

AI Browser Agent 自动操控浏览器搜索携程/去哪儿/同程三大平台，实时截图直播比价。

**Live Demo**: [hotel.rxcloud.group](https://hotel.rxcloud.group)

## Screenshots

### Search Form
输入酒店名称和日期，点击"开始比价"启动 AI Agent。

![Search Form](docs/screenshot-search.png)

### Agent Boot Animation
CRT 终端风格启动动画，三个平台同时初始化 Chromium 浏览器。

![Boot Animation](docs/screenshot-boot.png)

### Live Screenshot Streaming
Agent 操控浏览器搜索酒店，每个步骤的截图实时推送到前端。

![Live Streaming](docs/screenshot-results.png)

## 架构

```
Frontend (Next.js)          Supabase              Worker (Python)
hotel.rxcloud.group    evljxrlicctchscyfuan       Railway
      |                      |                      |
      |-- insert task ------>|                      |
      |                      |<-- poll pending ----|
      |                      |--- mark running --->|
      |                      |                      |-- browser-use Agent
      |                      |<-- step_logs -------|    (Chromium headless)
      |<-- poll 3s ----------|<-- screenshots -----|
      |                      |<-- results ---------|
      |<-- poll 3s ----------|                      |
```

| Layer | Stack | Deployment |
|-------|-------|------------|
| Frontend | Next.js 16 + Tailwind | Vercel |
| Database | Supabase (PostgreSQL + Storage) | Supabase Cloud |
| Worker | Python + browser-use + Playwright | Railway |
| LLM | GLM-4-Plus (OpenAI-compatible) | ZhiPu AI |

## Features

- CRT boot animation while waiting for browser agent to start
- Real-time screenshot streaming from headless Chromium
- 3-second polling for step logs, results, and task status
- Price validation (rejects year numbers, dates, garbage values)
- Sequential search across 3 platforms with per-platform error isolation

## Local Development

### Frontend

```bash
cd web
cp .env.local.example .env.local  # Set NEXT_PUBLIC_SUPABASE_URL and KEY
npm install
npm run dev
```

### Worker

```bash
cd browser-use-version
cp .env.example .env  # Set SUPABASE_URL, SUPABASE_KEY, OPENAI_BASE_URL, OPENAI_MODEL
uv sync
uv run playwright install chromium
uv run python worker.py
```

## Two Engine Comparison

This project implements the same hotel comparison task with two different Browser Agent approaches:

| Dimension | browser-use (server) | page-agent (client) |
|-----------|---------------------|-------------------|
| Runtime | Python + Playwright (headless) | Chrome Extension (user browser) |
| LLM | GLM-4-Plus via API | OpenAI API |
| Deployment | Railway (Docker) | Local Chrome |
| Observability | Screenshots + step logs | Console logs |
| Anti-bot | Headless detection risk | Real user browser |
