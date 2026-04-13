"""多策略重试编排器 — 每个平台支持多种搜索策略，失败自动切换"""

from typing import Any, Final

from platform_config import PlatformConfig
from hotel_compare import HotelPrice
from reflection import analyze_failure, is_plausible_result


RETRY_STRATEGIES: Final[dict[str, list[dict[str, Any]]]] = {
    "携程": [
        {"name": "desktop", "url": "https://hotels.ctrip.com/", "max_steps": 25},
        {"name": "mobile", "url": "https://m.ctrip.com/hotel/", "max_steps": 20},
    ],
    "去哪儿": [
        {"name": "direct", "url": "https://hotel.qunar.com/", "max_steps": 25},
        {"name": "portal", "url": "https://www.qunar.com/", "max_steps": 25},
        {"name": "mobile", "url": "https://touch.qunar.com/h5/hotel/", "max_steps": 20},
    ],
    "同程": [
        {"name": "main", "url": "https://www.ly.com/", "max_steps": 25},
        {"name": "mobile", "url": "https://m.ly.com/hotel/", "max_steps": 20},
    ],
}


def _attach_strategy_meta(result: HotelPrice, name: str, attempt: int) -> HotelPrice:
    """将重试策略元数据挂载到结果对象上（供 Worker 写入数据库）。"""
    # type: ignore[attr-defined]
    result._strategy_name = name  # noqa: SLF001
    result._attempt_number = attempt  # noqa: SLF001
    return result


async def search_with_retry(
    config: PlatformConfig,
    hotel: str,
    checkin: str,
    checkout: str,
    logs: list[dict[str, Any]],
    task_id: str | None = None,
    extra_context: str = "",
) -> HotelPrice | None:
    """尝试多种策略搜索平台，返回第一个有效结果。

    Args:
        config: 平台配置
        hotel: 酒店名称
        checkin: 入住日期
        checkout: 离店日期
        logs: 步骤日志列表
        task_id: 任务ID（启用 Supabase 流式回调）
        extra_context: 历史成功操作上下文

    Returns:
        HotelPrice 或 None
    """
    from agent_factory import run_platform_search
    from context_store import retrieve_relevant_context
    from supabase_client import insert_step_log

    # 获取历史成功操作上下文
    if not extra_context:
        try:
            extra_context = retrieve_relevant_context(config.name)
        except Exception:
            extra_context = ""

    strategies = RETRY_STRATEGIES.get(
        config.name,
        [{"name": "default", "url": config.urls[0], "max_steps": 15}],
    )

    for attempt, strategy in enumerate(strategies):
        print(f"  [{config.name}] 尝试策略: {strategy['name']} ({attempt + 1}/{len(strategies)})")

        result = await run_platform_search(
            config, hotel, checkin, checkout, logs, task_id,
            strategy_override=strategy,
            extra_context=extra_context,
        )

        if result and is_plausible_result(result, hotel):
            _attach_strategy_meta(result, strategy["name"], attempt + 1)
            print(f"  [{config.name}] 策略 '{strategy['name']}' 成功")
            return result

        # 分析失败原因
        failure_mode = analyze_failure(logs, config.name)
        print(f"  [{config.name}] 策略 '{strategy['name']}' 失败 ({failure_mode})")

        # 记录策略切换到 step_logs
        if task_id:
            insert_step_log(
                task_id, config.name, 900 + attempt,
                f"策略 '{strategy['name']}' 失败 ({failure_mode})，尝试下一个策略...", "",
                engine="browser-use",
            )

        # 验证码无法通过重试解决
        if failure_mode == "captcha":
            print(f"  [{config.name}] 遇到验证码，跳过剩余策略")
            break

    return None
