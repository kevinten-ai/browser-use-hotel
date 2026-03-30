"""Tests for reflection.py — failure analysis and result validation.

These functions directly determine whether a retry happens and what
strategy to try next. The 'no_logs' bug that caused all strategies
to exhaust on production was caught by these tests.
"""

import pytest
from reflection import analyze_failure, is_plausible_result


# ─── analyze_failure ─────────────────────────────────────────────────────

class TestAnalyzeFailure:
    def test_no_logs(self):
        assert analyze_failure([], "携程") == "no_logs"

    def test_no_matching_platform(self):
        logs = [{"platform": "去哪儿", "goal": "some goal"}]
        assert analyze_failure(logs, "携程") == "no_logs"

    def test_captcha_detected_chinese(self):
        logs = [
            {"platform": "携程", "goal": "点击搜索按钮"},
            {"platform": "携程", "goal": "遇到验证码滑块"},
            {"platform": "携程", "goal": "尝试拖动滑块"},
        ]
        assert analyze_failure(logs, "携程") == "captcha"

    def test_captcha_detected_english(self):
        logs = [
            {"platform": "携程", "goal": "click search"},
            {"platform": "携程", "goal": "captcha detected"},
            {"platform": "携程", "goal": "try solve captcha"},
        ]
        assert analyze_failure(logs, "携程") == "captcha"

    def test_login_wall_detected(self):
        logs = [
            {"platform": "去哪儿", "goal": "打开酒店页面"},
            {"platform": "去哪儿", "goal": "需要登录才能查看价格"},
            {"platform": "去哪儿", "goal": "尝试关闭登录弹窗"},
        ]
        assert analyze_failure(logs, "去哪儿") == "login_wall"

    def test_captcha_has_priority_over_login(self):
        """When both captcha and login keywords appear, captcha wins
        because it's checked first."""
        logs = [
            {"platform": "携程", "goal": "登录"},
            {"platform": "携程", "goal": "验证码"},
            {"platform": "携程", "goal": "test"},
        ]
        assert analyze_failure(logs, "携程") == "captcha"

    def test_navigation_stuck(self):
        """Same goal repeated 5+ times indicates stuck Agent."""
        logs = [
            {"platform": "同程", "goal": "点击酒店按钮"},
            {"platform": "同程", "goal": "点击酒店按钮"},
            {"platform": "同程", "goal": "点击酒店按钮"},
            {"platform": "同程", "goal": "点击酒店按钮"},
            {"platform": "同程", "goal": "点击酒店按钮"},
        ]
        assert analyze_failure(logs, "同程") == "navigation_stuck"

    def test_not_stuck_with_varied_goals(self):
        logs = [
            {"platform": "同程", "goal": "打开首页"},
            {"platform": "同程", "goal": "点击酒店"},
            {"platform": "同程", "goal": "输入搜索"},
            {"platform": "同程", "goal": "设置日期"},
            {"platform": "同程", "goal": "点击搜索"},
        ]
        assert analyze_failure(logs, "同程") == "unknown"

    def test_not_stuck_with_few_logs(self):
        """Navigation stuck requires >= 5 logs."""
        logs = [
            {"platform": "同程", "goal": "same"},
            {"platform": "同程", "goal": "same"},
            {"platform": "同程", "goal": "same"},
        ]
        assert analyze_failure(logs, "同程") == "unknown"

    def test_missing_goal_key(self):
        """Logs without 'goal' key should not crash."""
        logs = [
            {"platform": "携程"},
            {"platform": "携程"},
            {"platform": "携程"},
        ]
        # Should return "unknown" — empty goals don't match any pattern
        result = analyze_failure(logs, "携程")
        assert result in ("unknown", "no_logs")

    def test_mixed_platforms_filtered(self):
        """Only logs matching the given platform are analyzed."""
        logs = [
            {"platform": "携程", "goal": "正常搜索"},
            {"platform": "去哪儿", "goal": "遇到验证码"},  # Different platform
            {"platform": "携程", "goal": "继续搜索"},
            {"platform": "携程", "goal": "提取价格"},
        ]
        assert analyze_failure(logs, "携程") == "unknown"


# ─── is_plausible_result ─────────────────────────────────────────────────

class TestIsPlausibleResult:
    def test_valid_result(self, sample_hotel_price):
        assert is_plausible_result(sample_hotel_price, "北京国贸大酒店") is True

    def test_zero_price(self, sample_hotel_price):
        sample_hotel_price.lowest_price = 0
        assert is_plausible_result(sample_hotel_price, "test") is False

    def test_negative_price(self, sample_hotel_price):
        sample_hotel_price.lowest_price = -100
        assert is_plausible_result(sample_hotel_price, "test") is False

    def test_excessive_price(self, sample_hotel_price):
        sample_hotel_price.lowest_price = 99999
        assert is_plausible_result(sample_hotel_price, "test") is False

    def test_empty_room_type(self, sample_hotel_price):
        sample_hotel_price.room_type = ""
        assert is_plausible_result(sample_hotel_price, "test") is False

    def test_whitespace_room_type(self, sample_hotel_price):
        sample_hotel_price.room_type = "   "
        assert is_plausible_result(sample_hotel_price, "test") is False

    def test_boundary_price_30(self, sample_hotel_price):
        sample_hotel_price.lowest_price = 30
        assert is_plausible_result(sample_hotel_price, "test") is True

    def test_boundary_price_50000(self, sample_hotel_price):
        sample_hotel_price.lowest_price = 50000
        assert is_plausible_result(sample_hotel_price, "test") is True
