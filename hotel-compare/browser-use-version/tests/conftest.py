"""Shared test fixtures for hotel-compare tests."""

import sys
import os
import pytest
from unittest.mock import MagicMock

# Add parent dir to path so we can import modules directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set dummy env vars before any module tries to read them
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", "test-key")


@pytest.fixture
def sample_hotel_price():
    """A valid HotelPrice instance for testing."""
    from hotel_compare import HotelPrice
    return HotelPrice(
        platform="携程",
        hotel_name="北京国贸大酒店",
        lowest_price=888.0,
        room_type="豪华大床房",
        url="https://hotels.ctrip.com/hotel/123456",
    )


@pytest.fixture
def mock_agent_output():
    """Mock browser-use AgentOutput for callback tests."""
    output = MagicMock()
    output.thinking = "我看到搜索框在页面顶部"
    output.evaluation_previous_goal = "成功打开了携程首页"
    output.memory = "已输入酒店名称，准备搜索"
    output.next_goal = "点击搜索按钮"
    output.action = [MagicMock()]
    output.action[0].model_dump.return_value = {"click": {"index": 42}}
    # Backward compat property
    output.current_state = MagicMock()
    output.current_state.next_goal = "点击搜索按钮"
    return output


@pytest.fixture
def mock_browser_state():
    """Mock browser-use BrowserStateSummary."""
    state = MagicMock()
    state.url = "https://hotels.ctrip.com/"
    state.screenshot = None  # No screenshot by default
    return state
