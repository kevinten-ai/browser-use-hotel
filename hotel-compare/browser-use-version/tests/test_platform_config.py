"""Tests for platform_config.py — config integrity and template rendering.

Template rendering bugs are silent killers: the Agent gets a malformed
prompt and silently fails. These tests catch KeyError/formatting issues
before they reach production.
"""

import pytest
from platform_config import (
    PlatformConfig, ROBUSTNESS_RULES,
    CTRIP_CONFIG, QUNAR_CONFIG, TONGCHENG_CONFIG, ALL_PLATFORMS,
)


class TestPlatformConfigStructure:
    def test_all_platforms_count(self):
        assert len(ALL_PLATFORMS) == 3

    def test_unique_keys(self):
        keys = [p.key for p in ALL_PLATFORMS]
        assert len(keys) == len(set(keys))

    def test_unique_names(self):
        names = [p.name for p in ALL_PLATFORMS]
        assert len(names) == len(set(names))

    def test_all_have_urls(self):
        for p in ALL_PLATFORMS:
            assert len(p.urls) >= 1, f"{p.name} has no URLs"

    def test_ctrip_key(self):
        assert CTRIP_CONFIG.key == "ctrip"

    def test_qunar_key(self):
        assert QUNAR_CONFIG.key == "qunar"

    def test_tongcheng_key(self):
        assert TONGCHENG_CONFIG.key == "tongcheng"


class TestRobustnessRules:
    def test_not_empty(self):
        assert len(ROBUSTNESS_RULES) > 0

    def test_contains_key_terms(self):
        assert "登录弹窗" in ROBUSTNESS_RULES
        assert "验证码" in ROBUSTNESS_RULES
        assert "广告" in ROBUSTNESS_RULES


class TestTemplateRendering:
    """Test that .format() on each template works with expected params."""

    @pytest.mark.parametrize("config", ALL_PLATFORMS, ids=lambda c: c.key)
    def test_template_renders_without_error(self, config):
        result = config.task_template.format(
            hotel="北京国贸大酒店",
            checkin="2026-04-15",
            checkout="2026-04-17",
            url=config.urls[0],
        )
        assert "北京国贸大酒店" in result
        assert "2026-04-15" in result
        assert "2026-04-17" in result

    @pytest.mark.parametrize("config", ALL_PLATFORMS, ids=lambda c: c.key)
    def test_template_url_substituted(self, config):
        result = config.task_template.format(
            hotel="test", checkin="2026-01-01", checkout="2026-01-02",
            url="https://custom-url.com/",
        )
        assert "https://custom-url.com/" in result

    @pytest.mark.parametrize("config", ALL_PLATFORMS, ids=lambda c: c.key)
    def test_template_json_braces_preserved(self, config):
        """Double braces {{ }} should produce literal { } after .format()."""
        result = config.task_template.format(
            hotel="test", checkin="2026-01-01", checkout="2026-01-02",
            url="https://test.com",
        )
        # Should have literal JSON braces, not Python KeyError
        assert '{"platform"' in result or '{"price"' in result or "JSON" in result

    def test_special_chars_in_hotel_name(self):
        """Hotel names with special characters should not break formatting."""
        result = CTRIP_CONFIG.task_template.format(
            hotel='山西饭店 (五星级)',
            checkin="2026-04-15",
            checkout="2026-04-17",
            url="https://hotels.ctrip.com/",
        )
        assert "山西饭店 (五星级)" in result
