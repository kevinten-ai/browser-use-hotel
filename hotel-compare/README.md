<p align="center">
  <img src="docs/illustration-ai-compare.png" width="420" />
</p>

# 酒店跨平台比价 — AI Browser Agent 实战项目

AI Agent 自动操控浏览器，在携程、去哪儿、同程三大平台搜索酒店价格，实时截图直播比价。

**Live Demo**: [hotel.rxcloud.group](https://hotel.rxcloud.group)

---

## Screenshots

<table>
<tr>
<td align="center" width="33%">
<img src="docs/screenshot-search.png" width="280" /><br/>
<b>搜索表单</b><br/>
<sub>输入酒店名称和日期，选择引擎</sub>
</td>
<td align="center" width="33%">
<img src="docs/screenshot-boot.png" width="280" /><br/>
<b>CRT 启动动画</b><br/>
<sub>三平台 Agent 同时初始化</sub>
</td>
<td align="center" width="33%">
<img src="docs/screenshot-results.png" width="280" /><br/>
<b>实时截图 + 思考过程</b><br/>
<sub>Agent 操控浏览器搜索中</sub>
</td>
</tr>
</table>

---

## 这个项目能教你什么

这是一个完整的 **GUI Agent** 实战项目。通过这个项目你可以学到:

| 领域 | 学习要点 |
|:-----|:---------|
| **Browser Agent** | browser-use 的感知-行动循环、DOM 提取、Agent 参数调优 |
| **Playwright** | CDP 协议原理、headless Chromium、截图捕获 |
| **LLM 应用** | Prompt 工程、结构化输出、多模态 Vision、extend_system_message |
| **Agent 架构** | 反思机制、多策略重试、上下文学习、错误恢复 |
| **全栈部署** | Vercel + Railway + Supabase 三件套、任务队列模式 |
| **双引擎对比** | 服务端 Agent vs 客户端 Agent 的本质区别 |

---

## 技术架构

```
┌──────────────────────────────────────────────────────────────┐
│                     用户浏览器                                 │
│  ┌─────────────────┐     ┌─────────────────────────────────┐ │
│  │  Next.js 前端    │     │  Chrome Extension (page-agent)  │ │
│  │  hotel.rxcloud   │     │  在真实浏览器标签页内运行 Agent   │ │
│  └───────┬─────────┘     └────────────────┬────────────────┘ │
└──────────┼─────────────────────────────────┼─────────────────┘
           │ 创建 task / 轮询 step_logs       │ 轮询 pending tasks
           ▼                                 ▼
┌──────────────────────────────────────────────────────────────┐
│                   Supabase (PostgreSQL)                       │
│  tasks | step_logs | results | operation_contexts            │
│  Storage: screenshots bucket                                 │
└──────────────────────┬───────────────────────────────────────┘
                       │ Worker 轮询 pending tasks
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                   Railway (Python Worker)                     │
│                                                              │
│  worker.py → retry_strategies.py → agent_factory.py          │
│   任务轮询      多策略重试             统一 Agent 创建          │
│                                          │                   │
│  reflection.py   context_store.py    browser-use Agent       │
│   失败分析        操作上下文存储       Playwright + GLM-4.6V   │
└──────────────────────────────────────────────────────────────┘
```

### 技术栈

| 层 | 技术 | 角色 |
|:---|:-----|:-----|
| **Agent 框架** | browser-use 0.12+ (81k Stars) | 服务端: LLM 解析 DOM → 推理 → Playwright 执行 |
| **Agent 框架** | page-agent (JS) | 客户端: Chrome Extension 注入页面，直接操控 DOM |
| **浏览器驱动** | Playwright | 通过 CDP (Chrome DevTools Protocol) WebSocket 控制 Chromium |
| **LLM** | 智谱 GLM-4.6V-Flash | 免费多模态模型，支持 vision，128K 上下文，OpenAI 兼容 |
| **前端** | Next.js 16 + React 19 + Tailwind 4 | Vercel 部署，3s 轮询实时更新 |
| **数据库** | Supabase PostgreSQL + Storage | 任务队列 + 步骤日志 + 截图 + Realtime |
| **Worker** | Python 3.11 + Docker | Railway 托管，headless Chromium |

---

## 核心原理: Browser Agent 如何工作

### browser-use 的感知-行动循环

```
while step < max_steps:
    1. DOMService 注入 buildDomTree.js
       → 提取精简 DOM 树 (过滤不可交互元素，分配数字 ID)

    2. (use_vision=True) 截取页面截图

    3. 发送给 LLM: [DOM 树 + 截图 + 历史上下文 + system_message]

    4. LLM 返回:
       ├── thinking: "我看到搜索框在页面顶部..."
       ├── evaluation_previous_goal: "成功输入了酒店名称"
       ├── memory: "已找到3个搜索结果"
       ├── next_goal: "点击第一个匹配的酒店进入详情页"
       └── action: [click(element_id=42)]

    5. Playwright 执行 action (click/type/scroll/navigate...)

    6. 触发 register_new_step_callback
       → 上传截图到 Supabase Storage
       → 保存 thinking/evaluation/memory/actions 到 step_logs

    7. 检查是否完成 (done / max_steps / max_failures)
```

### Playwright 与 Chrome 的关系

```
Playwright (Python)   ─── CDP WebSocket ───>   Chromium (浏览器进程)
                          JSON 命令:
                          • DOM.querySelector      ← 查找元素
                          • Input.dispatchMouseEvent ← 点击
                          • Page.navigate           ← 导航
                          • Page.captureScreenshot   ← 截图
```

**关键理解:**
- Playwright 启动的是 **Chromium** (开源)，不是 Chrome (Google 发行版)
- 每次 `BrowserSession()` 创建全新实例，**没有** 你的 cookie/登录态 (刻意隔离)
- CDP 就是 F12 开发者工具背后的协议，Playwright 本质上是"用代码操作 DevTools"

### browser-use vs page-agent 本质区别

| 维度 | browser-use (服务端) | page-agent (客户端) |
|:-----|:---------------------|:--------------------|
| **运行环境** | Railway Docker 容器 | 用户的 Chrome 浏览器 |
| **浏览器** | 全新 Chromium (无 cookie) | 真实 Chrome (有登录态) |
| **感知方式** | DOM 提取 + 截图 → LLM | 直接读取页面 DOM → LLM |
| **反爬** | 容易被检测为自动化 | 难以区分于真人 |
| **部署** | 零安装，服务端运行 | 需装 Chrome Extension |
| **成本** | 服务器费用 | 客户端免费 |

---

## 六大增强机制

### 1. 鲁棒性 — 反干扰规则 + Vision

```python
# agent_factory.py — 增强参数
Agent(
    use_vision=True,              # 看截图识别弹窗/验证码
    max_failures=7,               # 允许更多失败
    enable_planning=True,         # 启用规划能力
    planning_replan_on_stall=2,   # 卡住2步就重新规划
    extend_system_message="""     # 注入到 Agent 的 system prompt
        登录弹窗: 点X → 点外部 → ESC → 忽略
        验证码: 立即放弃当前路径
        操作连续失败2次: 换完全不同的路径
    """,
)
```

### 2. 富进度显示 — Agent 推理链可视化

之前 `register_new_step_callback` 只保存截图，现在提取 AgentOutput 的全部字段:

```python
# hotel_compare.py — 回调中提取
thinking = agent_output.thinking                    # "搜索框在页面顶部"
evaluation = agent_output.evaluation_previous_goal  # "成功打开了酒店列表"
memory = agent_output.memory                        # "已找到北京国贸大酒店"
actions = [a.model_dump() for a in agent_output.action]  # [{click: {index: 42}}]
```

前端 `StepTimeline` (步骤时间线) + `StepDetailPanel` (思考/评估/记忆) 完整展示。

### 3. 反思机制 — 失败模式分析

```python
# reflection.py
def analyze_failure(logs, platform_name) -> str:
    """分析最后几步日志，返回: captcha | login_wall | navigation_stuck | unknown"""
    # 验证码 → 无法绕过，直接放弃
    # 登录墙 → 可以换移动站
    # 导航卡死 → 可以换策略
```

### 4. 错误恢复 — 多策略重试

```python
# retry_strategies.py
RETRY_STRATEGIES = {
    "携程": [
        {"name": "desktop", "url": "https://hotels.ctrip.com/"},      # 策略1: 桌面站
        {"name": "mobile",  "url": "https://m.ctrip.com/hotel/"},     # 策略2: 移动站
        {"name": "list_only", "prompt_suffix": "直接从列表提取价格"},    # 策略3: 不进详情页
    ],
}
# 自动按顺序尝试，验证码则提前终止
```

### 5. 上下文学习 — 从历史中学习

```python
# context_store.py — register_done_callback 在每次搜索完成后触发
store_operation_context(platform, hotel, success, history_list)
# 保存: 导航路径、每步目标、使用的策略

# 下次搜索时自动检索并注入 prompt
context = retrieve_relevant_context("携程")
# → "策略: desktop, 路径: hotels.ctrip.com → 搜索结果 → 酒店详情页
#    目标1: 在搜索框输入酒店名  目标2: 点击搜索  目标3: 点击匹配酒店"
```

### 6. 双引擎对比 — 量化 A/B 测试

前端 `SearchForm` 支持三种模式:
- **Browser-Use**: 只用服务端 Agent
- **Page-Agent**: 只用 Chrome Extension
- **Both (对比模式)**: 并行运行，`DualEngineView` 并排展示，`EngineComparisonTable` 量化对比

---

## 数据库设计

```sql
-- 5 个迁移文件，渐进式扩展

tasks (任务队列)
├── id, hotel, checkin, checkout
├── status: pending → running → completed
└── engine: browser-use | page-agent | dual     -- 005 新增

step_logs (Agent 每步推理记录)
├── task_id, platform, step_num
├── goal, screenshot_url                         -- 001 初始
├── thinking, evaluation, memory, actions, url   -- 002 新增
└── engine                                       -- 005 新增

results (最终比价结果)
├── task_id, platform, hotel_name, lowest_price, room_type
├── error                                        -- 失败原因
├── strategy_name, attempt_number                -- 003 新增
├── engine, duration_seconds                     -- 005 新增

operation_contexts (历史操作上下文)                 -- 004 新表
├── platform, hotel_pattern, success
├── steps_json (JSONB), navigation_path (text[])
└── strategy_name, duration_seconds
```

**设计要点:** Supabase 作为"穷人版消息队列" — Worker 每 5s 轮询 `SELECT WHERE status='pending'`，原子更新为 `running`。对低并发场景足够用，避免引入 RabbitMQ 等重依赖。

---

## 项目结构

```
hotel-compare/
├── browser-use-version/          # Python Worker (服务端 Agent)
│   ├── platform_config.py        # 平台配置: URL、Prompt 模板、反干扰规则
│   ├── agent_factory.py          # 统一 Agent 创建: vision + robustness + done_callback
│   ├── hotel_compare.py          # 核心: HotelPrice 模型、回调、解析
│   ├── worker.py                 # 任务轮询: Supabase → search_with_retry
│   ├── retry_strategies.py       # 多策略重试: desktop → mobile → list_only
│   ├── reflection.py             # 反思: 失败分析 + 结果验证
│   ├── context_store.py          # 上下文: 存储/检索历史成功路径
│   ├── supabase_client.py        # Supabase 封装
│   ├── app.py                    # Streamlit 本地调试 UI
│   └── Dockerfile                # Railway 部署: Python + Chromium + Playwright
│
├── page-agent-version/           # Chrome Extension (客户端 Agent)
│   ├── manifest.json             # MV3, module service worker
│   ├── background.js             # 任务编排 + Supabase 桥接 + 10s 轮询
│   ├── content.js                # 注入 page-agent 到页面上下文
│   ├── supabase-bridge.js        # 轻量 fetch-based Supabase REST 客户端
│   └── lib/page-agent.iife.js    # page-agent 库 (IIFE)
│
├── web/                          # Next.js 前端
│   ├── app/page.tsx              # 主页面: 轮询 + 单/双引擎路由
│   ├── components/
│   │   ├── SearchForm.tsx        # 搜索表单 + 引擎选择器 (3 选项)
│   │   ├── PlatformCard.tsx      # 截图 + 进度条 + 思考覆盖层 + 时间线
│   │   ├── StepTimeline.tsx      # 步骤圆点时间线 (可点击)
│   │   ├── StepDetailPanel.tsx   # 步骤详情: thinking/evaluation/memory/actions
│   │   ├── DualEngineView.tsx    # 双引擎并排视图
│   │   ├── EngineComparisonTable # 引擎对比: 价格/速度/胜率
│   │   ├── ComparisonTable.tsx   # 单引擎比价表
│   │   └── BootAnimation.tsx     # CRT 终端启动动画
│   └── lib/
│       ├── types.ts              # StepLog (含 thinking/eval/actions) + Result
│       └── supabase.ts           # Supabase 匿名客户端
│
└── supabase/migrations/          # 5 个渐进式迁移
    ├── 001_init.sql              # 基础: tasks + step_logs + results + RLS
    ├── 002_rich_progress.sql     # step_logs += thinking/evaluation/memory/actions
    ├── 003_retry_tracking.sql    # results += strategy_name/attempt_number
    ├── 004_operation_context.sql # 新表 operation_contexts
    └── 005_dual_engine.sql       # 全表 += engine 列
```

---

## 快速开始

### 环境要求

- Python 3.11+ / Node.js 18+
- Supabase 项目 (免费)
- 智谱 API Key ([GLM Coding Plan](https://open.bigmodel.cn/special_area) 免费)

### 1. Worker

```bash
cd hotel-compare/browser-use-version
cp .env.example .env   # 填入 API Key + Supabase 配置
pip install uv && uv sync
uv run playwright install chromium
uv run python worker.py
```

### 2. 前端

```bash
cd hotel-compare/web
npm install && npm run dev
# http://localhost:3000
```

### 3. 数据库

在 Supabase SQL Editor 依次执行 `supabase/migrations/001-005`，创建 Storage bucket `screenshots` (Public)。

### 4. Chrome Extension (可选，用于 page-agent)

Chrome → `chrome://extensions` → 开发者模式 → 加载 `hotel-compare/page-agent-version/`

---

## 部署

| 组件 | 平台 | 说明 |
|:-----|:-----|:-----|
| 前端 | [Vercel](https://vercel.com) | GitHub 推送自动部署，域名 hotel.rxcloud.group |
| Worker | [Railway](https://railway.com) | Dockerfile 部署，安装 Chromium + Playwright |
| 数据库 | [Supabase](https://supabase.com) | PostgreSQL + Storage + Realtime |

---

## License

MIT
