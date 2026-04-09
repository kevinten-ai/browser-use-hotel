#!/usr/bin/env python3
"""
本地 Agent 端到端测试脚本。
用于验证 browser-use + LLM 是否能正确操控浏览器并提取价格。

使用方法:
    cd hotel-compare/browser-use-version
    uv run python test_local_agent.py

    # 指定平台 (ctrip/qunar/tongcheng)
    uv run python test_local_agent.py --platform ctrip

    # 指定酒店
    uv run python test_local_agent.py --hotel "北京国贸大酒店"

注意: 会打开可见浏览器窗口（headless=False），方便观察 Agent 行为。
"""

import asyncio
import argparse
import os
import time
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from browser_use import Agent, BrowserSession

from agent_factory import create_default_llm


# 最简化测试 prompt — 不使用 platform_config 模板，直接硬编码
TEST_PROMPTS = {
    "ctrip": """
去携程搜索酒店价格。

操作步骤：
1. 打开 https://hotels.ctrip.com/
2. 在搜索框输入：{hotel}
3. 设置入住日期：{checkin}，离店日期：{checkout}
4. 点击搜索
5. 在搜索结果中找到名称最匹配的酒店，点击进入详情页
6. 在详情页找到最低房价和房型名称

如果弹出登录框或广告，点击关闭按钮。
同一操作最多重复2次，失败就换方法。

用JSON回复：
{{"platform": "携程", "hotel_name": "酒店名", "lowest_price": 数字, "room_type": "房型名", "url": "当前URL"}}

如果无法获取价格，回复：
{{"platform": "携程", "hotel_name": "", "lowest_price": 0, "room_type": "", "url": ""}}
""",
    "qunar": """
去去哪儿搜索酒店价格。

操作步骤：
1. 打开 https://hotel.qunar.com/
2. 如果页面没有搜索框，尝试打开 https://www.qunar.com/ 后点击酒店导航
3. 在搜索框中先清空默认文字，再输入：{hotel}
4. 设置入住日期：{checkin}，离店日期：{checkout}
5. 点击搜索
6. 在搜索结果中找到名称最匹配的酒店，点击进入详情页
7. 在详情页找到最低房价和房型名称

如果弹出登录框或广告，点击关闭按钮。
如果遇到验证码，放弃本次搜索。

用JSON回复：
{{"platform": "去哪儿", "hotel_name": "酒店名", "lowest_price": 数字, "room_type": "房型名", "url": "当前URL"}}

如果无法获取价格，回复：
{{"platform": "去哪儿", "hotel_name": "", "lowest_price": 0, "room_type": "", "url": ""}}
""",
    "tongcheng": """
去同程旅行搜索酒店价格。

操作步骤：
1. 打开 https://www.ly.com/
2. 找到并点击"酒店"入口
3. 在搜索框中输入：{hotel}
4. 设置入住日期：{checkin}，离店日期：{checkout}
5. 点击搜索
6. 在搜索结果中找到名称最匹配的酒店，点击进入详情页
7. 在详情页找到最低房价和房型名称

不要直接访问 hotel.ly.com (会返回403)，必须从 ly.com 首页进入。
如果弹出登录框或广告，点击关闭按钮。

用JSON回复：
{{"platform": "同程", "hotel_name": "酒店名", "lowest_price": 数字, "room_type": "房型名", "url": "当前URL"}}

如果无法获取价格，回复：
{{"platform": "同程", "hotel_name": "", "lowest_price": 0, "room_type": "", "url": ""}}
""",
}


async def test_single_platform(platform_key: str, hotel: str, checkin: str, checkout: str) -> list[dict[str, Any]]:
    """测试单个平台的 Agent 搜索能力"""

    model = os.getenv("OPENAI_MODEL", "glm-4-plus")
    base_url = os.getenv("OPENAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")

    print(f"\n{'=' * 60}")
    print(f"测试平台: {platform_key}")
    print(f"酒店: {hotel}")
    print(f"日期: {checkin} → {checkout}")
    print(f"模型: {model}")
    print(f"{'=' * 60}\n")

    llm = create_default_llm(model=model, base_url=base_url)

    prompt = TEST_PROMPTS[platform_key].format(
        hotel=hotel, checkin=checkin, checkout=checkout,
    )

    # 可见浏览器，方便观察
    browser = BrowserSession(
        headless=False,
        wait_between_actions=1.5,
        minimum_wait_page_load_time=3.0,
    )

    # 记录每一步
    steps_log: list[dict[str, Any]] = []

    async def on_step(browser_state, agent_output, step_num):
        goal = ""
        if agent_output:
            goal = agent_output.next_goal or ""
        url = browser_state.url if browser_state else "N/A"
        steps_log.append({"step": step_num, "goal": goal, "url": url})
        print(f"  Step {step_num}: {goal[:80]}")
        print(f"    URL: {url[:80]}")

    agent = Agent(
        task=prompt,
        llm=llm,
        browser=browser,
        register_new_step_callback=on_step,
        use_vision=False,
        max_actions_per_step=3,
    )

    start = time.time()
    try:
        result = await agent.run(max_steps=15)
        elapsed = time.time() - start

        print(f"\n{'─' * 60}")
        print(f"完成! 用时: {elapsed:.1f}s, 步数: {len(steps_log)}")

        if result:
            final = result.final_result()
            print(f"Agent 输出:\n{final}")
            urls = result.urls()
            if urls:
                print(f"最终 URL: {urls[-1]}")
        else:
            print("Agent 返回 None")

    except Exception as e:
        elapsed = time.time() - start
        print(f"\n❌ 异常: {e}")
        print(f"用时: {elapsed:.1f}s, 步数: {len(steps_log)}")

    finally:
        await browser.stop()

    return steps_log


async def main() -> None:
    parser = argparse.ArgumentParser(description="本地 Agent 测试")
    parser.add_argument("--hotel", default="北京国贸大酒店", help="酒店名称")
    parser.add_argument("--checkin", default="2026-04-15", help="入住日期")
    parser.add_argument("--checkout", default="2026-04-17", help="离店日期")
    parser.add_argument("--platform", default="ctrip",
                        choices=["ctrip", "qunar", "tongcheng", "all"],
                        help="测试平台")
    args = parser.parse_args()

    if args.platform == "all":
        for key in ["ctrip", "qunar", "tongcheng"]:
            await test_single_platform(key, args.hotel, args.checkin, args.checkout)
    else:
        await test_single_platform(args.platform, args.hotel, args.checkin, args.checkout)


if __name__ == "__main__":
    asyncio.run(main())
