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
    """Run a single platform search with full robustness features."""

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "glm-4.7"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
        dont_force_structured_output=True,
    )

    # Build task prompt from template — robustness rules go INTO the prompt
    # (not extend_system_message, which interferes with browser-use's internal prompts)
    url = (strategy_override or {}).get("url", config.urls[0])
    max_steps = (strategy_override or {}).get("max_steps", 25)
    prompt_suffix = (strategy_override or {}).get("prompt_suffix", "")
    task_prompt = config.task_template.format(
        hotel=hotel, checkin=checkin, checkout=checkout, url=url,
    )
    if prompt_suffix:
        task_prompt += f"\n\n{prompt_suffix}"
    # Append robustness rules to the task prompt
    task_prompt += f"\n\n{ROBUSTNESS_RULES}"
    if extra_context:
        task_prompt += f"\n\n历史成功操作参考：\n{extra_context}"

    browser = BrowserSession(
        headless=(task_id is not None),
        wait_between_actions=1.5,
        minimum_wait_page_load_time=3.0,
    )

    if task_id:
        _supabase_cb = make_streaming_callback(config.name, task_id, browser)
        async def callback(browser_state, agent_output, step_num):
            await _supabase_cb(browser_state, agent_output, step_num)
            goal = (agent_output.next_goal if agent_output else "") or ""
            logs.append({"platform": config.name, "step": step_num, "goal": goal})
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

    # Keep Agent params minimal — closer to original working config.
    # glm-4-plus struggles with complex AgentOutput schemas (45 validation errors
    # when planning/extra fields are required). Simpler = fewer LLM parse failures.
    agent = Agent(
        task=task_prompt,
        llm=llm,
        browser=browser,
        register_new_step_callback=callback,
        register_done_callback=on_done,
        use_vision=False,
        max_actions_per_step=3,
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
