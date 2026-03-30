"""Tests for parse_hotel_price — the most critical function.

This is where real-world Agent output gets parsed into structured data.
Every failure mode we saw in production maps to a test case here.
"""

import pytest
from hotel_compare import parse_hotel_price, _is_valid_price, HotelPrice


# ─── _is_valid_price ─────────────────────────────────────────────────────

class TestIsValidPrice:
    def test_valid_minimum(self):
        assert _is_valid_price(30) is True

    def test_valid_maximum(self):
        assert _is_valid_price(50000) is True

    def test_valid_typical(self):
        assert _is_valid_price(358) is True
        assert _is_valid_price(1280) is True

    def test_below_minimum(self):
        assert _is_valid_price(29.99) is False
        assert _is_valid_price(0) is False
        assert _is_valid_price(-100) is False

    def test_above_maximum(self):
        assert _is_valid_price(50000.01) is False
        assert _is_valid_price(100000) is False

    def test_year_as_price_rejected(self):
        """Year numbers like 2026 should pass range check (30-50000) but
        the prompt instructs the Agent not to return years. This test
        documents that _is_valid_price alone can't reject years."""
        assert _is_valid_price(2026) is True  # Range check passes

    def test_nan(self):
        """NaN comparisons always return False."""
        assert _is_valid_price(float("nan")) is False

    def test_infinity(self):
        assert _is_valid_price(float("inf")) is False


# ─── parse_hotel_price — JSON extraction ─────────────────────────────────

class TestParseHotelPriceJSON:
    def test_valid_json_with_lowest_price(self):
        text = '{"platform": "携程", "hotel_name": "山西饭店", "lowest_price": 358, "room_type": "标准间", "url": "https://ctrip.com/123"}'
        result = parse_hotel_price(text, "携程")
        assert result is not None
        assert result.lowest_price == 358
        assert result.hotel_name == "山西饭店"
        assert result.room_type == "标准间"

    def test_valid_json_with_price_field(self):
        """Fallback: 'price' field instead of 'lowest_price'."""
        text = '{"platform": "携程", "hotel_name": "测试酒店", "price": 500, "room_type": "大床房", "url": ""}'
        result = parse_hotel_price(text, "携程")
        assert result is not None
        assert result.lowest_price == 500

    def test_json_embedded_in_text(self):
        """Agent often returns JSON wrapped in text."""
        text = '搜索结果如下：\n{"platform": "去哪儿", "hotel_name": "测试", "lowest_price": 299, "room_type": "标间", "url": "https://qunar.com"}\n以上是搜索结果。'
        result = parse_hotel_price(text, "去哪儿")
        assert result is not None
        assert result.lowest_price == 299

    def test_json_with_invalid_price_rejected(self):
        text = '{"platform": "携程", "hotel_name": "测试", "lowest_price": 0, "room_type": "标间", "url": ""}'
        result = parse_hotel_price(text, "携程")
        assert result is None  # price 0 is below 30

    def test_json_with_year_as_price(self):
        """A common bug: Agent returns year as price."""
        text = '{"platform": "同程", "hotel_name": "测试", "lowest_price": 2026, "room_type": "标间", "url": ""}'
        result = parse_hotel_price(text, "同程")
        # 2026 passes range check (30-50000), so this returns a result
        assert result is not None
        assert result.lowest_price == 2026

    def test_json_with_missing_url_uses_fallback(self):
        text = '{"platform": "携程", "hotel_name": "测试", "lowest_price": 500, "room_type": "大床房"}'
        result = parse_hotel_price(text, "携程", fallback_url="https://fallback.com")
        assert result is not None
        assert result.url == "https://fallback.com"


# ─── parse_hotel_price — regex fallback ──────────────────────────────────

class TestParseHotelPriceRegex:
    def test_yen_sign_price(self):
        text = "最低价格是 ¥358 的标准间"
        result = parse_hotel_price(text, "携程")
        assert result is not None
        assert result.lowest_price == 358

    def test_fullwidth_yen_sign(self):
        text = "价格：￥1280"
        result = parse_hotel_price(text, "去哪儿")
        assert result is not None
        assert result.lowest_price == 1280

    def test_price_with_comma(self):
        text = "豪华套房 ¥1,280 起"
        result = parse_hotel_price(text, "同程")
        assert result is not None
        assert result.lowest_price == 1280

    def test_price_with_decimal(self):
        text = "特价 ¥358.5"
        result = parse_hotel_price(text, "携程")
        assert result is not None
        assert result.lowest_price == 358.5

    def test_regex_rejects_low_price(self):
        text = "仅 ¥10 优惠券"
        result = parse_hotel_price(text, "携程")
        assert result is None  # 10 < 30


# ─── parse_hotel_price — edge cases ──────────────────────────────────────

class TestParseHotelPriceEdgeCases:
    def test_none_text(self):
        assert parse_hotel_price(None, "携程") is None

    def test_empty_text(self):
        assert parse_hotel_price("", "携程") is None

    def test_no_price_in_text(self):
        text = "抱歉，无法获取价格信息"
        assert parse_hotel_price(text, "携程") is None

    def test_malformed_json(self):
        text = '{"lowest_price": abc}'
        assert parse_hotel_price(text, "携程") is None

    def test_failure_json_with_zero_price(self):
        """Agent returns failure JSON (all zeros)."""
        text = '{"platform": "携程", "hotel_name": "", "lowest_price": 0, "room_type": "", "url": ""}'
        assert parse_hotel_price(text, "携程") is None
