"""操作上下文存储 — 保存成功操作序列，为后续搜索注入历史经验"""

from supabase_client import get_client


def store_operation_context(platform, hotel, success, history_list,
                            strategy_name=None, duration=None):
    """从 AgentHistoryList 提取并保存压缩后的操作序列。

    Args:
        platform: 平台名称
        hotel: 酒店名称
        success: 是否成功获取价格
        history_list: browser-use AgentHistoryList 对象
        strategy_name: 使用的策略名称
        duration: 搜索耗时（秒）
    """
    steps_summary = []
    urls = []

    for h in history_list.history:
        if h.model_output:
            step = {
                "goal": h.model_output.next_goal,
                "actions": ([a.model_dump() for a in h.model_output.action]
                           if h.model_output.action else []),
                "evaluation": h.model_output.evaluation_previous_goal,
            }
            steps_summary.append(step)
        if h.state and h.state.url:
            urls.append(h.state.url)

    # 去重保留顺序
    seen = set()
    unique_urls = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

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


def retrieve_relevant_context(platform, limit=3) -> str:
    """检索该平台的历史成功操作上下文，格式化为 prompt 注入文本。

    Args:
        platform: 平台名称
        limit: 最多返回几条历史记录

    Returns:
        格式化的上下文字符串，空字符串表示无历史数据
    """
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

    if not resp.data:
        return ""

    lines = []
    for ctx in resp.data:
        strategy = ctx.get("strategy_name", "default")
        nav = " → ".join((ctx.get("navigation_path") or [])[:5])
        lines.append(f"- 策略: {strategy}, 路径: {nav}")
        for step in (ctx.get("steps_json") or [])[:5]:
            lines.append(f"  - 目标: {step.get('goal', '?')}")

    return "\n".join(lines)
