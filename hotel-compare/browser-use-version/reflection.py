"""反思模块 — 失败分析与结果验证"""

from typing import Any

from hotel_compare import HotelPrice


def analyze_failure(logs: list[dict[str, Any]], platform_name: str) -> str:
    """分析步骤日志，判断失败模式。

    Args:
        logs: 步骤日志列表，每条包含 platform, goal 等字段
        platform_name: 平台名称，用于过滤日志

    Returns:
        失败模式字符串: login_wall, captcha, navigation_stuck, no_logs, unknown
    """
    platform_logs = [entry for entry in logs if entry.get("platform") == platform_name]
    if not platform_logs:
        return "no_logs"

    last_goals = [entry.get("goal", "") for entry in platform_logs[-3:]]
    goals_text = " ".join(last_goals).lower()

    _captcha_keywords = frozenset(["验证码", "滑块", "captcha", "verify"])
    _login_keywords = frozenset(["登录", "login", "注册", "sign in"])
    if any(w in goals_text for w in _captcha_keywords):
        return "captcha"
    if any(w in goals_text for w in _login_keywords):
        return "login_wall"
    if len(set(last_goals)) <= 1 and len(platform_logs) >= 5:
        return "navigation_stuck"
    return "unknown"


def is_plausible_result(result: HotelPrice, hotel: str) -> bool:
    """检查搜索结果是否合理。

    Args:
        result: HotelPrice 实例
        hotel: 搜索的酒店名

    Returns:
        结果是否通过合理性检查
    """
    if result.lowest_price <= 0 or result.lowest_price > 50000:
        return False
    if not result.room_type or result.room_type.strip() == "":
        return False
    return True
