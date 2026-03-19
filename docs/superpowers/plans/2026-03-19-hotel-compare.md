# 酒店跨平台比价工具 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a hotel price comparison tool that searches the same hotel on Ctrip, Qunar, and Tongcheng using two approaches (browser-use and page-agent), with visual UI for each.

**Architecture:** Two independent sub-projects in `hotel-compare/`. Version A uses Python browser-use + Streamlit (server-side agent). Version B uses page-agent Chrome extension (client-side agent). Both do the same job: take hotel name + dates, search 3 platforms, output a comparison table.

**Tech Stack:**
- Version A: Python 3.11+, browser-use 0.12+, Streamlit, langchain-openai
- Version B: TypeScript, page-agent (alibaba/page-agent), Chrome Extension Manifest V3

---

## File Structure

```
hotel-compare/
├── browser-use-version/
│   ├── hotel_compare.py        # Core logic: 3 search functions + compare + main
│   ├── app.py                  # Streamlit UI: input form + progress + results table
│   ├── requirements.txt        # browser-use, streamlit, langchain-openai, python-dotenv
│   ├── .env.example            # OPENAI_API_KEY=your-key-here
│   └── pyproject.toml          # uv project config (python >= 3.11)
│
├── page-agent-version/
│   ├── manifest.json           # Chrome extension manifest V3
│   ├── popup.html              # Extension popup: input form + results table
│   ├── popup.js                # Popup logic: send task to background, display results
│   ├── background.js           # Service worker: orchestrate MultiPageAgent cross-tab
│   ├── content.js              # Content script: page-agent DOM controller
│   └── lib/
│       └── page-agent.iife.js  # page-agent bundled library (from CDN)
│
└── README.md                   # Usage guide + comparison notes
```

---

## Chunk 1: browser-use Version

### Task 1: Project Setup

**Files:**
- Create: `hotel-compare/browser-use-version/pyproject.toml`
- Create: `hotel-compare/browser-use-version/.env.example`
- Create: `hotel-compare/browser-use-version/requirements.txt`

- [ ] **Step 1: Create project directory and pyproject.toml**

```bash
mkdir -p hotel-compare/browser-use-version
```

```toml
# hotel-compare/browser-use-version/pyproject.toml
[project]
name = "hotel-compare"
version = "0.1.0"
description = "Hotel price comparison using browser-use agent"
requires-python = ">=3.11"
dependencies = [
    "browser-use>=0.12.0",
    "langchain-openai",
    "streamlit",
    "python-dotenv",
]
```

- [ ] **Step 2: Create .env.example**

```bash
# hotel-compare/browser-use-version/.env.example
OPENAI_API_KEY=your-openai-api-key-here
```

- [ ] **Step 3: Create requirements.txt**

```
browser-use>=0.12.0
langchain-openai
streamlit
python-dotenv
```

- [ ] **Step 4: Initialize uv project and install dependencies**

```bash
cd hotel-compare/browser-use-version
uv init --no-readme
uv add browser-use langchain-openai streamlit python-dotenv
uv sync
```

Expected: `.venv/` created with Python 3.11+ and all dependencies installed.

- [ ] **Step 5: Install Chromium for Playwright**

```bash
cd hotel-compare/browser-use-version
uv run playwright install chromium
```

Expected: Chromium browser downloaded for Playwright.

- [ ] **Step 6: Commit**

```bash
git add hotel-compare/browser-use-version/pyproject.toml hotel-compare/browser-use-version/.env.example hotel-compare/browser-use-version/requirements.txt
git commit -m "feat: scaffold browser-use hotel compare project"
```

---

### Task 2: Core Logic — hotel_compare.py

**Files:**
- Create: `hotel-compare/browser-use-version/hotel_compare.py`

- [ ] **Step 1: Create hotel_compare.py with Pydantic model and search functions**

```python
# hotel-compare/browser-use-version/hotel_compare.py
"""
酒店跨平台比价工具 — browser-use 版本
=====================================
学习目标：
  1. browser-use Agent 创建与配置
  2. Task prompt 设计技巧
  3. Pydantic 结构化输出 (output_model_schema)
  4. 回调函数追踪执行过程
  5. 错误处理：单平台失败不影响整体
"""

import asyncio
import argparse
import time
import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# ========================================
# 📚 学习点 1: 结构化输出模型
# ----------------------------------------
# browser-use 的 output_model_schema 参数接收一个 Pydantic BaseModel，
# Agent 会将最终结果解析为该模型的实例。
# 这比让 Agent 返回自由文本后再解析要可靠得多。
# ========================================

class HotelPrice(BaseModel):
    """单个平台的酒店价格结果"""
    platform: str = Field(description="平台名称，如 携程/去哪儿/同程")
    hotel_name: str = Field(description="酒店名称（平台上显示的实际名称）")
    lowest_price: float = Field(description="最低价格（人民币）")
    room_type: str = Field(description="最低价对应的房型名称")
    url: str = Field(description="搜索结果页面的 URL")


# ========================================
# 📚 学习点 2: 步骤回调函数
# ----------------------------------------
# register_new_step_callback 在每步 LLM 推理完成后触发。
# 参数：
#   - browser_state: 当前页面 URL、截图等
#   - agent_output: LLM 的推理结果（思考、动作选择）
#   - step_num: 第几步
# 这是实现"执行过程可视化"的关键 API。
# ========================================

def make_step_callback(platform_name: str, log_list: list):
    """创建一个步骤回调函数，记录每步执行详情"""
    async def on_step(browser_state, agent_output, step_num):
        log_entry = {
            "platform": platform_name,
            "step": step_num,
            "url": browser_state.url if browser_state else "N/A",
            "goal": agent_output.current_state.next_goal if agent_output and agent_output.current_state else "N/A",
            "actions": [a.model_dump() for a in agent_output.action] if agent_output else [],
        }
        log_list.append(log_entry)
        # 打印实时日志
        print(f"  [{platform_name}] Step {step_num}: {log_entry['goal']}")
    return on_step


# ========================================
# 📚 学习点 3: Agent 创建与 Task Prompt
# ----------------------------------------
# task 参数是自然语言描述，要写得具体：
#   - 告诉 Agent 去哪个网站
#   - 搜索什么内容
#   - 提取什么数据
# 不同网站需要不同的 prompt 策略，因为 UI 结构不同。
# ========================================

async def search_ctrip(hotel: str, checkin: str, checkout: str, logs: list) -> Optional[HotelPrice]:
    """
    在携程 (trip.com) 搜索酒店价格。
    学习重点：基本的 Agent 任务定义和结构化输出。
    """
    from browser_use import Agent, BrowserSession
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4o")
    browser = BrowserSession(headless=False)

    agent = Agent(
        task=f"""去 https://www.trip.com/hotels/ 搜索酒店。
步骤：
1. 在搜索框输入酒店名称：{hotel}
2. 设置入住日期：{checkin}
3. 设置离店日期：{checkout}
4. 点击搜索按钮
5. 在搜索结果中找到最匹配的酒店
6. 提取该酒店的最低价格、对应房型名称、和当前页面 URL

注意：
- 如果出现日期选择器弹窗，需要正确选择日期
- 只提取第一个最匹配的酒店结果
- 价格单位是人民币
- platform 字段填写"携程"
""",
        llm=llm,
        browser=browser,
        output_model_schema=HotelPrice,
        register_new_step_callback=make_step_callback("携程", logs),
        max_actions_per_step=5,
        use_vision=True,
    )

    try:
        result = await agent.run(max_steps=25)
        output = result.get_structured_output(HotelPrice)
        return output
    except Exception as e:
        print(f"  [携程] ❌ 搜索失败: {e}")
        return None
    finally:
        await browser.close()


async def search_qunar(hotel: str, checkin: str, checkout: str, logs: list) -> Optional[HotelPrice]:
    """
    在去哪儿 (qunar.com) 搜索酒店价格。
    学习重点：不同网站的 UI 差异如何影响 task prompt。
    """
    from browser_use import Agent, BrowserSession
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4o")
    browser = BrowserSession(headless=False)

    agent = Agent(
        task=f"""去 https://hotel.qunar.com/ 搜索酒店。
步骤：
1. 在搜索框输入酒店名称：{hotel}
2. 设置入住日期：{checkin}
3. 设置离店日期：{checkout}
4. 点击搜索按钮
5. 在搜索结果中找到最匹配的酒店
6. 提取该酒店的最低价格、对应房型名称、和当前页面 URL

注意：
- 去哪儿的搜索框可能需要先清空默认文本
- 如果有弹窗广告，先关闭它
- 价格单位是人民币
- platform 字段填写"去哪儿"
""",
        llm=llm,
        browser=browser,
        output_model_schema=HotelPrice,
        register_new_step_callback=make_step_callback("去哪儿", logs),
        max_actions_per_step=5,
        use_vision=True,
    )

    try:
        result = await agent.run(max_steps=25)
        output = result.get_structured_output(HotelPrice)
        return output
    except Exception as e:
        print(f"  [去哪儿] ❌ 搜索失败: {e}")
        return None
    finally:
        await browser.close()


async def search_tongcheng(hotel: str, checkin: str, checkout: str, logs: list) -> Optional[HotelPrice]:
    """
    在同程 (tongcheng.com) 搜索酒店价格。
    学习重点：处理更复杂的页面结构。
    """
    from browser_use import Agent, BrowserSession
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4o")
    browser = BrowserSession(headless=False)

    agent = Agent(
        task=f"""去 https://hotel.ly.com/ 搜索酒店。
步骤：
1. 在搜索框输入酒店名称：{hotel}
2. 设置入住日期：{checkin}
3. 设置离店日期：{checkout}
4. 点击搜索按钮
5. 在搜索结果中找到最匹配的酒店
6. 提取该酒店的最低价格、对应房型名称、和当前页面 URL

注意：
- 同程旅行的酒店域名是 hotel.ly.com
- 日期选择器可能需要多次点击切换月份
- 价格单位是人民币
- platform 字段填写"同程"
""",
        llm=llm,
        browser=browser,
        output_model_schema=HotelPrice,
        register_new_step_callback=make_step_callback("同程", logs),
        max_actions_per_step=5,
        use_vision=True,
    )

    try:
        result = await agent.run(max_steps=25)
        output = result.get_structured_output(HotelPrice)
        return output
    except Exception as e:
        print(f"  [同程] ❌ 搜索失败: {e}")
        return None
    finally:
        await browser.close()


# ========================================
# 📚 学习点 4: 结果汇总与对比
# ----------------------------------------
# 三个平台各自返回 HotelPrice 或 None（失败时）。
# 我们需要容错处理：某个平台失败不影响其他。
# ========================================

def compare_and_print(results: list[Optional[HotelPrice]]):
    """汇总三个平台的结果，格式化输出对比表"""
    valid = [r for r in results if r is not None]

    if not valid:
        print("\n❌ 所有平台搜索均失败")
        return

    # 按价格排序
    valid.sort(key=lambda x: x.lowest_price)

    print("\n" + "=" * 60)
    print(f"{'平台':<8} {'最低价':>8} {'房型':<16} {'链接'}")
    print("-" * 60)

    for i, r in enumerate(valid):
        marker = " 🏆" if i == 0 else ""
        print(f"{r.platform:<8} ¥{r.lowest_price:>7.0f} {r.room_type:<16} {r.url[:40]}...{marker}")

    print("=" * 60)

    if len(valid) >= 2:
        diff = valid[-1].lowest_price - valid[0].lowest_price
        print(f"\n💰 最低价: {valid[0].platform} ¥{valid[0].lowest_price:.0f}"
              f" (比最高价低 ¥{diff:.0f})")

    failed = [r for r in results if r is None]
    if failed:
        print(f"⚠️  {len(failed)} 个平台搜索失败")


# ========================================
# 📚 学习点 5: 主流程编排
# ----------------------------------------
# 顺序执行三个平台的搜索，每个都独立运行。
# 这样日志清晰，便于观察每个 Agent 的行为。
# 后续可以改为 asyncio.gather 并行执行。
# ========================================

async def run_comparison(hotel: str, checkin: str, checkout: str):
    """运行完整的比价流程，返回结果和日志"""
    logs = []
    results = []

    print(f"\n🏨 开始比价: {hotel} | {checkin} → {checkout}")
    print("=" * 60)

    platforms = [
        ("携程", search_ctrip),
        ("去哪儿", search_qunar),
        ("同程", search_tongcheng),
    ]

    for name, search_fn in platforms:
        print(f"\n🔍 正在搜索 {name}...")
        start = time.time()
        result = await search_fn(hotel, checkin, checkout, logs)
        elapsed = time.time() - start
        if result:
            print(f"  ✅ {name} 完成 ({elapsed:.1f}s) → ¥{result.lowest_price:.0f} {result.room_type}")
        else:
            print(f"  ❌ {name} 失败 ({elapsed:.1f}s)")
        results.append(result)

    compare_and_print(results)
    return results, logs


async def main():
    parser = argparse.ArgumentParser(description="酒店跨平台比价工具")
    parser.add_argument("--hotel", required=True, help="酒店名称")
    parser.add_argument("--checkin", required=True, help="入住日期 (YYYY-MM-DD)")
    parser.add_argument("--checkout", required=True, help="离店日期 (YYYY-MM-DD)")
    args = parser.parse_args()

    await run_comparison(args.hotel, args.checkin, args.checkout)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Test the script can be imported without errors**

```bash
cd hotel-compare/browser-use-version
uv run python -c "from hotel_compare import HotelPrice, compare_and_print; print('Import OK')"
```

Expected: `Import OK`

- [ ] **Step 3: Commit**

```bash
git add hotel-compare/browser-use-version/hotel_compare.py
git commit -m "feat: add browser-use hotel comparison core logic"
```

---

### Task 3: Streamlit UI — app.py

**Files:**
- Create: `hotel-compare/browser-use-version/app.py`

- [ ] **Step 1: Create Streamlit app**

```python
# hotel-compare/browser-use-version/app.py
"""
酒店跨平台比价 — Streamlit 可视化界面
======================================
学习目标：
  1. 用 Streamlit 快速搭建可视化界面
  2. 将 browser-use 的执行过程实时展示给用户
  3. 理解 Agent 回调函数如何与 UI 联动
"""

import streamlit as st
import asyncio
import time
from datetime import date, timedelta
from hotel_compare import (
    search_ctrip, search_qunar, search_tongcheng, HotelPrice
)

st.set_page_config(page_title="🏨 酒店跨平台比价", layout="wide")
st.title("🏨 酒店跨平台比价工具")
st.caption("基于 browser-use Agent — 服务端浏览器自动化方案")

# ── 输入区域 ──
col1, col2, col3 = st.columns(3)
with col1:
    hotel = st.text_input("酒店名称", value="北京国贸大酒店")
with col2:
    checkin = st.date_input("入住日期", value=date.today() + timedelta(days=7))
with col3:
    checkout = st.date_input("离店日期", value=date.today() + timedelta(days=9))

start_btn = st.button("🔍 开始比价", type="primary", use_container_width=True)

if start_btn:
    if not hotel:
        st.error("请输入酒店名称")
        st.stop()

    checkin_str = checkin.strftime("%Y-%m-%d")
    checkout_str = checkout.strftime("%Y-%m-%d")
    nights = (checkout - checkin).days

    st.markdown(f"**{hotel}** | {checkin_str} → {checkout_str} ({nights}晚)")
    st.divider()

    # ── 执行进度区域 ──
    logs = []
    results = []

    platforms = [
        ("携程", "trip.com", search_ctrip),
        ("去哪儿", "qunar.com", search_qunar),
        ("同程", "ly.com", search_tongcheng),
    ]

    progress = st.progress(0, text="准备中...")
    status_cols = st.columns(3)

    # 为每个平台创建状态展示区
    platform_status = {}
    for i, (name, domain, _) in enumerate(platforms):
        with status_cols[i]:
            platform_status[name] = {
                "container": st.container(border=True),
                "status": "⏳ 等待中",
            }
            platform_status[name]["container"].markdown(f"### {name}\n⏳ 等待中")

    # ── 日志区域 ──
    log_expander = st.expander("📋 Agent 执行日志", expanded=True)

    # ── 顺序执行搜索 ──
    for idx, (name, domain, search_fn) in enumerate(platforms):
        progress.progress(
            (idx) / len(platforms),
            text=f"正在搜索 {name}..."
        )
        platform_status[name]["container"].markdown(f"### {name}\n🔄 正在搜索...")

        start_time = time.time()
        result = asyncio.run(search_fn(hotel, checkin_str, checkout_str, logs))
        elapsed = time.time() - start_time

        results.append(result)

        # 更新平台状态
        if result:
            platform_status[name]["container"].markdown(
                f"### {name}\n"
                f"✅ 搜索完成 ({elapsed:.0f}s)\n\n"
                f"**¥{result.lowest_price:.0f}** {result.room_type}"
            )
        else:
            platform_status[name]["container"].markdown(
                f"### {name}\n"
                f"❌ 搜索失败 ({elapsed:.0f}s)"
            )

        # 更新日志
        platform_logs = [l for l in logs if l["platform"] == name]
        with log_expander:
            for log in platform_logs:
                st.text(f"[{log['platform']}] Step {log['step']}: {log['goal']}")

    progress.progress(1.0, text="完成!")

    # ── 对比结果表格 ──
    st.divider()
    st.subheader("📊 对比结果")

    valid_results = [r for r in results if r is not None]
    if valid_results:
        valid_results.sort(key=lambda x: x.lowest_price)

        # 表格数据
        table_data = []
        for i, r in enumerate(valid_results):
            table_data.append({
                "排名": f"{'🏆 ' if i == 0 else ''}{i+1}",
                "平台": r.platform,
                "最低价": f"¥{r.lowest_price:.0f}",
                "房型": r.room_type,
                "链接": r.url,
            })

        st.table(table_data)

        if len(valid_results) >= 2:
            diff = valid_results[-1].lowest_price - valid_results[0].lowest_price
            st.success(
                f"💰 最低价: **{valid_results[0].platform} ¥{valid_results[0].lowest_price:.0f}** "
                f"(比最高价低 ¥{diff:.0f})"
            )
    else:
        st.error("所有平台搜索均失败，请检查网络或重试")

    # ── 执行统计 ──
    st.divider()
    st.subheader("📈 执行统计")
    stat_cols = st.columns(3)
    stat_cols[0].metric("总步数", f"{len(logs)} 步")
    stat_cols[1].metric("成功平台", f"{len(valid_results)}/3")
    stat_cols[2].metric("日志条数", f"{len(logs)} 条")
```

- [ ] **Step 2: Verify Streamlit can start**

```bash
cd hotel-compare/browser-use-version
uv run streamlit run app.py --server.headless true &
sleep 3 && kill %1 2>/dev/null
```

Expected: Streamlit starts without import errors.

- [ ] **Step 3: Commit**

```bash
git add hotel-compare/browser-use-version/app.py
git commit -m "feat: add Streamlit UI for hotel comparison"
```

---

### Task 4: Smoke Test — Run Against One Platform

- [ ] **Step 1: Create .env with real API key**

```bash
cd hotel-compare/browser-use-version
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

- [ ] **Step 2: Run CLI against one platform to verify**

```bash
cd hotel-compare/browser-use-version
uv run python -c "
import asyncio
from hotel_compare import search_ctrip
logs = []
result = asyncio.run(search_ctrip('北京国贸大酒店', '2026-04-15', '2026-04-17', logs))
print('Result:', result)
print('Logs:', len(logs), 'steps')
"
```

Expected: Browser opens, navigates to trip.com, searches hotel, returns HotelPrice or error. Watch the browser and console output to understand what the Agent does at each step.

- [ ] **Step 3: If successful, run full comparison**

```bash
cd hotel-compare/browser-use-version
uv run python hotel_compare.py --hotel "北京国贸大酒店" --checkin 2026-04-15 --checkout 2026-04-17
```

- [ ] **Step 4: Commit any prompt adjustments**

After observing Agent behavior, you will likely need to adjust the task prompts in `hotel_compare.py` (e.g., more specific instructions for date pickers). Commit those changes.

```bash
git add hotel-compare/browser-use-version/hotel_compare.py
git commit -m "fix: refine agent task prompts based on testing"
```

---

## Chunk 2: page-agent Chrome Extension Version

### Task 5: Chrome Extension Scaffold

**Files:**
- Create: `hotel-compare/page-agent-version/manifest.json`
- Create: `hotel-compare/page-agent-version/popup.html`
- Create: `hotel-compare/page-agent-version/popup.js`
- Create: `hotel-compare/page-agent-version/background.js`
- Create: `hotel-compare/page-agent-version/content.js`

- [ ] **Step 1: Create manifest.json**

```json
{
  "manifest_version": 3,
  "name": "酒店比价助手 (page-agent)",
  "version": "1.0.0",
  "description": "基于 page-agent 的跨平台酒店比价工具",
  "permissions": [
    "activeTab",
    "tabs",
    "storage",
    "scripting"
  ],
  "host_permissions": [
    "https://www.trip.com/*",
    "https://hotel.qunar.com/*",
    "https://hotel.ly.com/*"
  ],
  "action": {
    "default_popup": "popup.html",
    "default_title": "酒店比价"
  },
  "background": {
    "service_worker": "background.js",
    "type": "module"
  },
  "content_scripts": [
    {
      "matches": [
        "https://www.trip.com/*",
        "https://hotel.qunar.com/*",
        "https://hotel.ly.com/*"
      ],
      "js": ["content.js"],
      "run_at": "document_idle"
    }
  ]
}
```

- [ ] **Step 2: Create popup.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { width: 420px; padding: 16px; font-family: -apple-system, sans-serif; font-size: 14px; }
    h1 { font-size: 18px; margin-bottom: 12px; }
    .form-group { margin-bottom: 12px; }
    label { display: block; font-weight: 600; margin-bottom: 4px; color: #333; }
    input { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
    .dates { display: flex; gap: 8px; }
    .dates input { flex: 1; }
    button { width: 100%; padding: 10px; background: #4F46E5; color: white;
             border: none; border-radius: 6px; font-size: 15px; cursor: pointer; font-weight: 600; }
    button:hover { background: #4338CA; }
    button:disabled { background: #9CA3AF; cursor: not-allowed; }

    .status { margin-top: 16px; }
    .platform-row { display: flex; align-items: center; padding: 8px;
                    border-bottom: 1px solid #f0f0f0; }
    .platform-name { width: 60px; font-weight: 600; }
    .platform-status { flex: 1; color: #666; }
    .platform-price { font-weight: 700; color: #059669; }
    .platform-best { background: #ECFDF5; border-radius: 4px; }

    .result-box { margin-top: 16px; padding: 12px; background: #F0FDF4;
                  border-radius: 8px; text-align: center; }
    .result-box .price { font-size: 24px; font-weight: 700; color: #059669; }

    .log { margin-top: 12px; max-height: 200px; overflow-y: auto;
           font-size: 12px; color: #666; background: #F9FAFB;
           padding: 8px; border-radius: 6px; }
    .log-entry { padding: 2px 0; border-bottom: 1px solid #F3F4F6; }
    .hidden { display: none; }
  </style>
</head>
<body>
  <h1>🏨 酒店跨平台比价</h1>

  <div class="form-group">
    <label>酒店名称</label>
    <input type="text" id="hotel" value="北京国贸大酒店" placeholder="输入酒店名称">
  </div>

  <div class="form-group">
    <label>日期</label>
    <div class="dates">
      <input type="date" id="checkin">
      <input type="date" id="checkout">
    </div>
  </div>

  <button id="startBtn" onclick="startCompare()">🔍 开始比价</button>

  <div id="statusSection" class="status hidden">
    <div id="ctripRow" class="platform-row">
      <span class="platform-name">携程</span>
      <span class="platform-status" id="ctripStatus">⏳ 等待中</span>
      <span class="platform-price" id="ctripPrice"></span>
    </div>
    <div id="qunarRow" class="platform-row">
      <span class="platform-name">去哪儿</span>
      <span class="platform-status" id="qunarStatus">⏳ 等待中</span>
      <span class="platform-price" id="qunarPrice"></span>
    </div>
    <div id="tongchengRow" class="platform-row">
      <span class="platform-name">同程</span>
      <span class="platform-status" id="tongchengStatus">⏳ 等待中</span>
      <span class="platform-price" id="tongchengPrice"></span>
    </div>
  </div>

  <div id="resultBox" class="result-box hidden">
    <div>💰 最低价</div>
    <div class="price" id="bestPrice"></div>
    <div id="bestPlatform" style="color: #666;"></div>
  </div>

  <div id="logSection" class="log hidden"></div>

  <script src="popup.js"></script>
</body>
</html>
```

- [ ] **Step 3: Create popup.js**

```javascript
// hotel-compare/page-agent-version/popup.js
/**
 * 酒店比价 Chrome 扩展 — popup 控制逻辑
 * ============================================
 * 📚 学习点:
 *   1. Chrome Extension popup 与 background 通信
 *   2. chrome.runtime.sendMessage / onMessage 消息机制
 *   3. 实时更新 UI 的模式
 */

// 初始化日期默认值
const today = new Date();
const checkinDate = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
const checkoutDate = new Date(today.getTime() + 9 * 24 * 60 * 60 * 1000);
document.getElementById('checkin').value = checkinDate.toISOString().split('T')[0];
document.getElementById('checkout').value = checkoutDate.toISOString().split('T')[0];

// 监听来自 background 的进度更新
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'PROGRESS') {
    updatePlatformStatus(msg.platform, msg.status, msg.data);
  }
  if (msg.type === 'LOG') {
    addLog(msg.text);
  }
  if (msg.type === 'COMPLETE') {
    onComplete(msg.results);
  }
});

async function startCompare() {
  const hotel = document.getElementById('hotel').value.trim();
  const checkin = document.getElementById('checkin').value;
  const checkout = document.getElementById('checkout').value;

  if (!hotel || !checkin || !checkout) {
    alert('请填写完整信息');
    return;
  }

  // 显示状态区域
  document.getElementById('statusSection').classList.remove('hidden');
  document.getElementById('logSection').classList.remove('hidden');
  document.getElementById('resultBox').classList.add('hidden');
  document.getElementById('startBtn').disabled = true;
  document.getElementById('startBtn').textContent = '🔄 搜索中...';

  // 重置状态
  ['ctrip', 'qunar', 'tongcheng'].forEach(id => {
    document.getElementById(id + 'Status').textContent = '⏳ 等待中';
    document.getElementById(id + 'Price').textContent = '';
    document.getElementById(id + 'Row').classList.remove('platform-best');
  });

  // 发送任务到 background
  chrome.runtime.sendMessage({
    type: 'START_COMPARE',
    hotel,
    checkin,
    checkout,
  });
}

function updatePlatformStatus(platform, status, data) {
  const idMap = { '携程': 'ctrip', '去哪儿': 'qunar', '同程': 'tongcheng' };
  const id = idMap[platform];
  if (!id) return;

  document.getElementById(id + 'Status').textContent = status;
  if (data && data.price) {
    document.getElementById(id + 'Price').textContent = `¥${data.price}`;
  }
}

function addLog(text) {
  const logSection = document.getElementById('logSection');
  const entry = document.createElement('div');
  entry.className = 'log-entry';
  entry.textContent = text;
  logSection.appendChild(entry);
  logSection.scrollTop = logSection.scrollHeight;
}

function onComplete(results) {
  document.getElementById('startBtn').disabled = false;
  document.getElementById('startBtn').textContent = '🔍 开始比价';

  const valid = results.filter(r => r && r.price);
  if (valid.length === 0) {
    document.getElementById('resultBox').classList.remove('hidden');
    document.getElementById('bestPrice').textContent = '搜索失败';
    document.getElementById('bestPlatform').textContent = '请重试';
    return;
  }

  valid.sort((a, b) => a.price - b.price);
  const best = valid[0];

  // 高亮最低价平台
  const idMap = { '携程': 'ctrip', '去哪儿': 'qunar', '同程': 'tongcheng' };
  const bestId = idMap[best.platform];
  if (bestId) {
    document.getElementById(bestId + 'Row').classList.add('platform-best');
  }

  // 显示结果
  document.getElementById('resultBox').classList.remove('hidden');
  document.getElementById('bestPrice').textContent = `¥${best.price}`;
  document.getElementById('bestPlatform').textContent = `${best.platform} · ${best.roomType}`;
}
```

- [ ] **Step 4: Create background.js (service worker)**

```javascript
// hotel-compare/page-agent-version/background.js
/**
 * 酒店比价 — Background Service Worker
 * ======================================
 * 📚 学习点:
 *   1. page-agent 的跨标签页使用模式
 *   2. Chrome Extension tabs API
 *   3. content script 注入与通信
 *
 * 核心流程:
 *   popup 发送 START_COMPARE
 *   → background 依次打开 3 个标签页
 *   → 每个标签页注入 content.js
 *   → content.js 中的 page-agent 执行搜索
 *   → 结果回传给 popup
 */

const PLATFORMS = [
  {
    name: '携程',
    url: 'https://www.trip.com/hotels/',
    buildTask: (hotel, checkin, checkout) =>
      `在这个页面搜索酒店"${hotel}"，入住日期${checkin}，离店日期${checkout}。找到最匹配的酒店，告诉我最低价格和房型名称。用JSON格式回复：{"price": 数字, "roomType": "房型名", "hotelName": "酒店名"}`,
  },
  {
    name: '去哪儿',
    url: 'https://hotel.qunar.com/',
    buildTask: (hotel, checkin, checkout) =>
      `在这个页面搜索酒店"${hotel}"，入住日期${checkin}，离店日期${checkout}。找到最匹配的酒店，告诉我最低价格和房型名称。用JSON格式回复：{"price": 数字, "roomType": "房型名", "hotelName": "酒店名"}`,
  },
  {
    name: '同程',
    url: 'https://hotel.ly.com/',
    buildTask: (hotel, checkin, checkout) =>
      `在这个页面搜索酒店"${hotel}"，入住日期${checkin}，离店日期${checkout}。找到最匹配的酒店，告诉我最低价格和房型名称。用JSON格式回复：{"price": 数字, "roomType": "房型名", "hotelName": "酒店名"}`,
  },
];

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'START_COMPARE') {
    runComparison(msg.hotel, msg.checkin, msg.checkout);
  }
  if (msg.type === 'AGENT_RESULT') {
    // 来自 content script 的搜索结果
    handleAgentResult(sender.tab?.id, msg.result);
  }
  if (msg.type === 'AGENT_LOG') {
    // 来自 content script 的日志
    broadcast({ type: 'LOG', text: `[${msg.platform}] ${msg.text}` });
  }
});

let pendingResults = {};
let completedCount = 0;
let totalPlatforms = 0;

async function runComparison(hotel, checkin, checkout) {
  pendingResults = {};
  completedCount = 0;
  totalPlatforms = PLATFORMS.length;

  for (const platform of PLATFORMS) {
    broadcast({
      type: 'PROGRESS',
      platform: platform.name,
      status: '🔄 正在打开页面...',
    });

    try {
      // 打开新标签页
      const tab = await chrome.tabs.create({ url: platform.url, active: false });

      // 等待页面加载完成
      await waitForTabLoad(tab.id);

      // 向 content script 发送搜索任务
      const task = platform.buildTask(hotel, checkin, checkout);
      chrome.tabs.sendMessage(tab.id, {
        type: 'RUN_AGENT',
        task,
        platform: platform.name,
      });

      // 记录标签页 ID 与平台的对应关系
      pendingResults[tab.id] = { platform: platform.name, tabId: tab.id };

      broadcast({
        type: 'PROGRESS',
        platform: platform.name,
        status: '🤖 Agent 搜索中...',
      });
    } catch (err) {
      broadcast({
        type: 'PROGRESS',
        platform: platform.name,
        status: `❌ 失败: ${err.message}`,
      });
      completedCount++;
      checkAllDone();
    }
  }
}

function handleAgentResult(tabId, result) {
  const info = pendingResults[tabId];
  if (!info) return;

  info.result = result;
  completedCount++;

  if (result && result.success) {
    try {
      const data = JSON.parse(result.data);
      broadcast({
        type: 'PROGRESS',
        platform: info.platform,
        status: '✅ 完成',
        data: { price: data.price, roomType: data.roomType },
      });
      info.parsed = data;
    } catch {
      broadcast({
        type: 'PROGRESS',
        platform: info.platform,
        status: '⚠️ 结果解析失败',
      });
    }
  } else {
    broadcast({
      type: 'PROGRESS',
      platform: info.platform,
      status: '❌ 搜索失败',
    });
  }

  checkAllDone();
}

function checkAllDone() {
  if (completedCount < totalPlatforms) return;

  const results = Object.values(pendingResults).map(info => {
    if (info.parsed) {
      return {
        platform: info.platform,
        price: info.parsed.price,
        roomType: info.parsed.roomType,
        hotelName: info.parsed.hotelName,
      };
    }
    return null;
  });

  broadcast({ type: 'COMPLETE', results });
}

function waitForTabLoad(tabId) {
  return new Promise((resolve) => {
    function listener(updatedTabId, changeInfo) {
      if (updatedTabId === tabId && changeInfo.status === 'complete') {
        chrome.tabs.onUpdated.removeListener(listener);
        // 额外等待 2 秒让页面 JS 执行完
        setTimeout(resolve, 2000);
      }
    }
    chrome.tabs.onUpdated.addListener(listener);
  });
}

function broadcast(msg) {
  chrome.runtime.sendMessage(msg).catch(() => {
    // popup 可能已关闭，忽略错误
  });
}
```

- [ ] **Step 5: Create content.js**

```javascript
// hotel-compare/page-agent-version/content.js
/**
 * 酒店比价 — Content Script
 * ===========================
 * 📚 学习点:
 *   1. page-agent 的页面内使用方式
 *   2. 如何在 content script 中动态加载第三方库
 *   3. page-agent 事件系统监听 Agent 执行过程
 *
 * 注意：page-agent 需要通过 <script> 标签注入到页面上下文中，
 * 因为它需要直接操作页面 DOM。content script 运行在隔离的 JS 上下文中。
 */

// 监听来自 background 的搜索任务
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'RUN_AGENT') {
    runPageAgent(msg.task, msg.platform);
    sendResponse({ received: true });
  }
  return true;
});

async function runPageAgent(task, platform) {
  try {
    log(platform, 'page-agent 初始化中...');

    // 动态注入 page-agent 脚本到页面上下文
    // 因为 content script 无法直接使用 page-agent 的 DOM 操作能力
    const result = await injectAndRun(task, platform);

    chrome.runtime.sendMessage({
      type: 'AGENT_RESULT',
      result,
    });
  } catch (err) {
    log(platform, `错误: ${err.message}`);
    chrome.runtime.sendMessage({
      type: 'AGENT_RESULT',
      result: { success: false, data: err.message },
    });
  }
}

function injectAndRun(task, platform) {
  return new Promise((resolve, reject) => {
    // 监听来自页面上下文的结果
    window.addEventListener('message', function handler(event) {
      if (event.data?.type === 'PAGE_AGENT_RESULT') {
        window.removeEventListener('message', handler);
        resolve(event.data.result);
      }
      if (event.data?.type === 'PAGE_AGENT_LOG') {
        log(platform, event.data.text);
      }
    });

    // 注入脚本到页面上下文
    const script = document.createElement('script');
    script.src = chrome.runtime.getURL('lib/page-agent.iife.js');
    script.onload = () => {
      // 注入执行代码
      const execScript = document.createElement('script');
      execScript.textContent = `
        (async () => {
          try {
            // page-agent 通过 IIFE 暴露为 window.PageAgent
            const agent = new window.PageAgent.PageAgentCore({
              // LLM 配置 — 用户需要替换为自己的 API Key
              provider: 'openai',
              model: 'gpt-4o',
              apiKey: '${getApiKey()}',
              baseURL: 'https://api.openai.com/v1',
              maxSteps: 25,
              language: 'zh-CN',
            });

            // 监听执行过程
            agent.addEventListener('activity', (e) => {
              const a = e.detail;
              if (a.type === 'executing') {
                window.postMessage({
                  type: 'PAGE_AGENT_LOG',
                  text: 'Step: ' + a.tool + '(' + JSON.stringify(a.input).substring(0, 80) + ')',
                }, '*');
              }
            });

            const result = await agent.execute(${JSON.stringify(task)});
            window.postMessage({ type: 'PAGE_AGENT_RESULT', result }, '*');
            agent.dispose();
          } catch (err) {
            window.postMessage({
              type: 'PAGE_AGENT_RESULT',
              result: { success: false, data: err.message },
            }, '*');
          }
        })();
      `;
      document.head.appendChild(execScript);
    };
    script.onerror = () => reject(new Error('Failed to load page-agent library'));
    document.head.appendChild(script);
  });
}

function getApiKey() {
  // TODO: 从 chrome.storage 读取用户配置的 API Key
  // 目前硬编码，后续改为配置页面
  return 'YOUR_API_KEY';
}

function log(platform, text) {
  chrome.runtime.sendMessage({
    type: 'AGENT_LOG',
    platform,
    text,
  }).catch(() => {});
}
```

- [ ] **Step 6: Download page-agent IIFE bundle**

```bash
mkdir -p hotel-compare/page-agent-version/lib
curl -L "https://cdn.jsdelivr.net/npm/page-agent@latest/dist/iife/page-agent.js" \
  -o hotel-compare/page-agent-version/lib/page-agent.iife.js
```

Update `manifest.json` to make the lib accessible from content scripts:

Add to manifest.json:
```json
  "web_accessible_resources": [
    {
      "resources": ["lib/page-agent.iife.js"],
      "matches": ["https://www.trip.com/*", "https://hotel.qunar.com/*", "https://hotel.ly.com/*"]
    }
  ]
```

- [ ] **Step 7: Commit**

```bash
git add hotel-compare/page-agent-version/
git commit -m "feat: add page-agent Chrome extension version"
```

---

### Task 6: Test page-agent Extension

- [ ] **Step 1: Load extension in Chrome**

1. Open `chrome://extensions/`
2. Enable Developer Mode
3. Click "Load unpacked" → select `hotel-compare/page-agent-version/`
4. Verify extension icon appears

- [ ] **Step 2: Configure API key**

Edit `content.js` and replace `YOUR_API_KEY` with a real OpenAI API key. (In a later iteration, this should be moved to a settings page stored in `chrome.storage`.)

- [ ] **Step 3: Test single platform**

Click the extension icon, enter a hotel name and dates, click "开始比价". Observe:
- Do 3 tabs open?
- Does the content script inject page-agent?
- Does the agent execute the search task?
- Do logs appear in the popup?

- [ ] **Step 4: Debug and fix issues**

Content script ↔ page context communication is the most likely failure point. Check Chrome DevTools console for errors in both the content script context and page context.

- [ ] **Step 5: Commit fixes**

```bash
git add hotel-compare/page-agent-version/
git commit -m "fix: debug page-agent extension integration"
```

---

## Chunk 3: README and Comparison

### Task 7: Write README with Comparison

**Files:**
- Create: `hotel-compare/README.md`

- [ ] **Step 1: Write README**

```markdown
# 🏨 酒店跨平台比价 — 双引擎对比

同一个任务（酒店比价），两种 BrowserAgent 技术路线。

## 快速开始

### browser-use 版本（服务端 Agent）

```bash
cd browser-use-version
cp .env.example .env  # 填入 OPENAI_API_KEY
uv sync
uv run streamlit run app.py
```

### page-agent 版本（客户端 Agent）

1. 打开 `chrome://extensions/`
2. 开启开发者模式
3. 加载 `page-agent-version/` 目录
4. 点击扩展图标开始比价

## 对比记录

运行两个版本后，填写实际数据：

| 维度 | browser-use | page-agent |
|------|------------|------------|
| 搜索成功率 | /3 | /3 |
| 总耗时 | s | s |
| Token 消耗 | tokens | tokens |
| 代码行数 | 行 | 行 |
| 部署依赖 | Python+Playwright | Chrome 扩展 |
| 调试体验 | /5 | /5 |
| 稳定性 | /5 | /5 |

## 学习笔记

### browser-use 关键收获
- ...

### page-agent 关键收获
- ...

### 两种路线的本质差异
- ...
```

- [ ] **Step 2: Commit**

```bash
git add hotel-compare/README.md
git commit -m "docs: add README with comparison template"
```

---

## Execution Order Summary

1. **Task 1** — Project setup (uv, dependencies)
2. **Task 2** — Core Python logic (hotel_compare.py)
3. **Task 3** — Streamlit UI (app.py)
4. **Task 4** — Smoke test browser-use version
5. **Task 5** — Chrome extension scaffold (page-agent)
6. **Task 6** — Test page-agent extension
7. **Task 7** — README and comparison document
