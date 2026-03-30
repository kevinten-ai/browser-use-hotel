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
import json
import re
import time
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# Platform configs are now in platform_config.py; Agent creation is in agent_factory.py.
# Lazy-import run_platform_search to avoid circular import at module load time.
from platform_config import CTRIP_CONFIG, QUNAR_CONFIG, TONGCHENG_CONFIG


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
        print(f"  [{platform_name}] Step {step_num}: {log_entry['goal']}")
    return on_step


def make_streaming_callback(platform_name: str, task_id: str, browser_session=None):
    """创建步骤回调：截图上传 Supabase + 写入 step_logs"""
    import sys
    import base64
    from supabase_client import upload_screenshot, insert_step_log

    # Use ASCII-safe platform name for storage paths
    platform_key = {"携程": "ctrip", "去哪儿": "qunar", "同程": "tongcheng"}.get(platform_name, platform_name)

    async def on_step(browser_state, agent_output, step_num):
        goal = (agent_output.next_goal
                if agent_output and agent_output.next_goal else "")
        screenshot_url = ""
        # Method 1: browser_state.screenshot (base64 from browser-use)
        screenshot_b64 = None
        if browser_state and browser_state.screenshot:
            screenshot_b64 = browser_state.screenshot
            print(f"  [{platform_name}] Step {step_num}: got screenshot from browser_state ({len(screenshot_b64)} chars)", flush=True)
        # Method 2: manual capture via BrowserSession.take_screenshot()
        if not screenshot_b64 and browser_session:
            try:
                screenshot_bytes = await browser_session.take_screenshot()
                if screenshot_bytes:
                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
                    print(f"  [{platform_name}] Step {step_num}: got screenshot from take_screenshot ({len(screenshot_b64)} chars)", flush=True)
            except Exception as e:
                print(f"  [{platform_name}] Step {step_num}: take_screenshot failed: {e}", flush=True)
        # Upload if we got a screenshot
        if screenshot_b64:
            try:
                screenshot_url = upload_screenshot(
                    task_id, platform_key, step_num, screenshot_b64
                )
                print(f"  [{platform_name}] Step {step_num}: uploaded -> {screenshot_url[:80]}", flush=True)
            except Exception as e:
                print(f"  [{platform_name}] Step {step_num}: upload failed: {e}", flush=True)
        else:
            print(f"  [{platform_name}] Step {step_num}: no screenshot available", flush=True)

        # Extract rich Agent reasoning data
        thinking = getattr(agent_output, 'thinking', None) if agent_output else None
        evaluation = getattr(agent_output, 'evaluation_previous_goal', None) if agent_output else None
        memory = getattr(agent_output, 'memory', None) if agent_output else None
        actions_data = ([a.model_dump() for a in agent_output.action]
                        if agent_output and hasattr(agent_output, 'action') and agent_output.action else None)
        page_url = browser_state.url if browser_state else None

        insert_step_log(task_id, platform_name, step_num, goal, screenshot_url,
                        thinking=thinking, evaluation=evaluation, memory=memory,
                        actions=actions_data, url=page_url)
        sys.stdout.flush()

    return on_step


def _is_valid_price(price: float) -> bool:
    """检查价格是否在合理范围内（排除年份、日期等误解析）"""
    return 30 <= price <= 50000


def parse_hotel_price(text: str, platform: str, fallback_url: str = "") -> Optional[HotelPrice]:
    """从 Agent 的自由文本输出中解析 HotelPrice。
    尝试提取 JSON，如果失败则用正则匹配关键字段。"""
    if not text:
        return None
    # 尝试提取 JSON 块
    json_match = re.search(r'\{[^{}]*"lowest_price"[^{}]*\}', text, re.DOTALL)
    if not json_match:
        json_match = re.search(r'\{[^{}]*"price"[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            price = float(data.get("lowest_price", data.get("price", 0)))
            if not _is_valid_price(price):
                print(f"  [{platform}] ⚠️ 解析到异常价格 ¥{price}，跳过")
                return None
            return HotelPrice(
                platform=data.get("platform", platform),
                hotel_name=data.get("hotel_name", data.get("hotelName", "")),
                lowest_price=price,
                room_type=data.get("room_type", data.get("roomType", "")),
                url=data.get("url", fallback_url),
            )
        except (json.JSONDecodeError, ValueError):
            pass
    # 降级：用正则提取价格（要求 ¥ 前缀，避免误提取年份等数字）
    price_match = re.search(r'[¥￥]\s*(\d[\d,]*\.?\d*)', text)
    if price_match:
        price = float(price_match.group(1).replace(',', ''))
        if _is_valid_price(price):
            return HotelPrice(
                platform=platform,
                hotel_name="",
                lowest_price=price,
                room_type="",
                url=fallback_url,
            )
    return None


# ========================================
# 📚 学习点 3: Agent 创建与 Task Prompt
# ----------------------------------------
# task 参数是自然语言描述，要写得具体：
#   - 告诉 Agent 去哪个网站
#   - 搜索什么内容
#   - 提取什么数据
# 不同网站需要不同的 prompt 策略，因为 UI 结构不同。
# ========================================

async def search_ctrip(hotel: str, checkin: str, checkout: str, logs: list, task_id=None) -> Optional[HotelPrice]:
    """在携程 (trip.com) 搜索酒店价格"""
    from agent_factory import run_platform_search
    return await run_platform_search(CTRIP_CONFIG, hotel, checkin, checkout, logs, task_id)


async def search_qunar(hotel: str, checkin: str, checkout: str, logs: list, task_id=None) -> Optional[HotelPrice]:
    """在去哪儿 (qunar.com) 搜索酒店价格"""
    from agent_factory import run_platform_search
    return await run_platform_search(QUNAR_CONFIG, hotel, checkin, checkout, logs, task_id)


async def search_tongcheng(hotel: str, checkin: str, checkout: str, logs: list, task_id=None) -> Optional[HotelPrice]:
    """在同程 (ly.com) 搜索酒店价格"""
    from agent_factory import run_platform_search
    return await run_platform_search(TONGCHENG_CONFIG, hotel, checkin, checkout, logs, task_id)


# ========================================
# 📚 学习点 4: 结果汇总与对比
# ----------------------------------------
# 三个平台各自返回 HotelPrice 或 None（失败时）。
# 容错处理：某个平台失败不影响其他。
# ========================================

def compare_and_print(results: list[Optional[HotelPrice]]):
    """汇总三个平台的结果，格式化输出对比表"""
    valid = [r for r in results if r is not None]

    if not valid:
        print("\n❌ 所有平台搜索均失败")
        return

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

    failed_count = len([r for r in results if r is None])
    if failed_count:
        print(f"⚠️  {failed_count} 个平台搜索失败")


# ========================================
# 📚 学习点 5: 主流程编排
# ----------------------------------------
# 顺序执行三个平台的搜索，每个都独立运行。
# 日志清晰，便于观察每个 Agent 的行为。
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
