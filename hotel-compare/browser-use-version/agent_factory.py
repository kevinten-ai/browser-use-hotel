"""Unified Agent creation for all platforms. Eliminates 3x duplication."""

import os
import time
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from browser_use import Agent, BrowserSession
from browser_use.llm.openai.chat import ChatOpenAI
from platform_config import PlatformConfig, ROBUSTNESS_RULES
from hotel_compare import HotelPrice, parse_hotel_price, make_step_callback, make_streaming_callback
from context_store import store_operation_context


async def run_platform_search(
    config: PlatformConfig,
    hotel: str,
    checkin: str,
    checkout: str,
    logs: list,
    task_id: str = None,
    strategy_override: dict = None,
    extra_context: str = "",
) -> Optional[HotelPrice]:
    """Run a single platform search with full robustness features.

    Args:
        config: Platform configuration (urls, task_template, hints, etc.)
        hotel: Hotel name to search for
        checkin: Check-in date (YYYY-MM-DD)
        checkout: Check-out date (YYYY-MM-DD)
        logs: List to append step logs to (used in CLI mode)
        task_id: If provided, enables headless mode + streaming callbacks to Supabase
        strategy_override: Optional dict with keys: url, max_steps, prompt_suffix
        extra_context: Optional historical success context to inject into system message
    """

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "glm-4.6v-flash"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
        dont_force_structured_output=True,
    )

    # Build task prompt from template
    url = (strategy_override or {}).get("url", config.urls[0])
    max_steps = (strategy_override or {}).get("max_steps", 15)
    prompt_suffix = (strategy_override or {}).get("prompt_suffix", "")
    task_prompt = config.task_template.format(
        hotel=hotel, checkin=checkin, checkout=checkout, url=url,
    )
    if prompt_suffix:
        task_prompt += f"\n\n{prompt_suffix}"

    # Build extend_system_message
    system_ext = ROBUSTNESS_RULES + "\n" + config.robustness_hints
    if extra_context:
        system_ext += f"\n\n历史成功操作参考：\n{extra_context}"

    browser = BrowserSession(headless=(task_id is not None))

    if task_id:
        callback = make_streaming_callback(config.name, task_id, browser)
    else:
        callback = make_step_callback(config.name, logs)

    # Track result for done_callback
    start_time = time.time()
    result_holder = {}
    strategy_name = (strategy_override or {}).get("name")

    async def on_done(history_list):
        duration = time.time() - start_time
        success = result_holder.get("result") is not None
        try:
            store_operation_context(
                config.name, hotel, success, history_list,
                strategy_name=strategy_name, duration=duration,
            )
        except Exception as e:
            print(f"  [{config.name}] Context store failed: {e}")

    agent = Agent(
        task=task_prompt,
        llm=llm,
        browser=browser,
        register_new_step_callback=callback,
        register_done_callback=on_done,
        use_vision=True,
        max_actions_per_step=5,
        max_failures=7,
        enable_planning=True,
        planning_replan_on_stall=2,
        extend_system_message=system_ext,
        final_response_after_failure=True,
    )

    try:
        result = await agent.run(max_steps=max_steps)
        result_text = result.final_result() if result else None
        url_final = result.urls()[-1] if result and result.urls() else ""
        if result_text:
            parsed = parse_hotel_price(result_text, config.name, url_final)
            result_holder["result"] = parsed
            return parsed
    except Exception as e:
        print(f"  [{config.name}] ❌ 搜索失败: {e}")
    finally:
        await browser.stop()

    return None
