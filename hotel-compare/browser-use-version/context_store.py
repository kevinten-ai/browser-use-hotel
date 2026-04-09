"""操作上下文存储 — 保存成功操作序列，为后续搜索注入历史经验"""

from typing import Any

from supabase_client import get_client


def store_operation_context(
    platform: str,
    hotel: str,
    success: bool,
    history_list: Any,
    strategy_name: str | None = None,
    duration: float | None = None,
) -> None:
    """从 AgentHistoryList 提取并保存压缩后的操作序列。

    Args:
        platform: 平台名称
        hotel: 酒店名称
        success: 是否成功获取价格
        history_list: browser-use AgentHistoryList 对象
        strategy_name: 使用的策略名称
        duration: 搜索耗时（秒）
    """
    steps_summary: list[dict[str, Any]] = []
    urls: list[str] = []

    try:
        history = history_list.history
    except AttributeError:
        history = []

    for h in history:
        if hasattr(h, "model_output") and h.model_output:
            model_output = h.model_output
            step = {
                "goal": getattr(model_output, "next_goal", None),
                "actions": (
                    [a.model_dump() for a in model_output.action]
                    if getattr(model_output, "action", None) else []
                ),
                "evaluation": getattr(model_output, "evaluation_previous_goal", None),
            }
            steps_summary.append(step)
        if hasattr(h, "state") and h.state and hasattr(h.state, "url") and h.state.url:
            urls.append(h.state.url)

    # 去重保留顺序
    seen: set[str] = set()
    unique_urls: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

    try:
        get_client().table("operation_contexts").insert({
            "platform": platform,
            "hotel_pattern": hotel,
            "success": success,
            "steps_json": steps_summary,
            "navigation_path": unique_urls,
            "total_steps": len(steps_summary),
            "duration_seconds": duration,
            "strategy_name": strategy_name,
        }).execute()
    except Exception as e:
        # 上下文存储失败不应阻塞主流程
        print(f"  [{platform}] Context store insert failed: {e}")


def retrieve_relevant_context(platform: str, limit: int = 3) -> str:
    """检索该平台的历史成功操作上下文，格式化为 prompt 注入文本。

    Args:
        platform: 平台名称
        limit: 最多返回几条历史记录

    Returns:
        格式化的上下文字符串，空字符串表示无历史数据
    """
    try:
        resp = (
            get_client()
            .table("operation_contexts")
            .select("steps_json, navigation_path, strategy_name")
            .eq("platform", platform)
            .eq("success", True)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
    except Exception:
        return ""

    if not resp.data:
        return ""

    lines: list[str] = []
    for ctx in resp.data:
        strategy = ctx.get("strategy_name", "default")
        nav_path = ctx.get("navigation_path") or []
        nav = " → ".join(nav_path[:5])
        lines.append(f"- 策略: {strategy}, 路径: {nav}")
        for step in (ctx.get("steps_json") or [])[:5]:
            lines.append(f"  - 目标: {step.get('goal', '?')}")

    return "\n".join(lines)
