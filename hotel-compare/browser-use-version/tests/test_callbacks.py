"""Tests for make_step_callback — the in-memory logging callback.

This callback populates the logs list used by analyze_failure.
The 'no_logs' production bug happened because streaming callback
didn't populate this list.
"""

import pytest
from hotel_compare import make_step_callback


class TestMakeStepCallback:
    @pytest.mark.asyncio
    async def test_appends_to_log_list(self, mock_browser_state, mock_agent_output):
        logs = []
        callback = make_step_callback("携程", logs)
        await callback(mock_browser_state, mock_agent_output, 1)
        assert len(logs) == 1

    @pytest.mark.asyncio
    async def test_log_entry_structure(self, mock_browser_state, mock_agent_output):
        logs = []
        callback = make_step_callback("携程", logs)
        await callback(mock_browser_state, mock_agent_output, 3)
        entry = logs[0]
        assert entry["platform"] == "携程"
        assert entry["step"] == 3
        assert entry["url"] == "https://hotels.ctrip.com/"

    @pytest.mark.asyncio
    async def test_none_browser_state(self, mock_agent_output):
        logs = []
        callback = make_step_callback("去哪儿", logs)
        await callback(None, mock_agent_output, 1)
        assert logs[0]["url"] == "N/A"

    @pytest.mark.asyncio
    async def test_none_agent_output(self, mock_browser_state):
        logs = []
        callback = make_step_callback("同程", logs)
        await callback(mock_browser_state, None, 1)
        assert logs[0]["goal"] == "N/A"
        assert logs[0]["actions"] == []

    @pytest.mark.asyncio
    async def test_multiple_steps(self, mock_browser_state, mock_agent_output):
        logs = []
        callback = make_step_callback("携程", logs)
        for i in range(5):
            await callback(mock_browser_state, mock_agent_output, i + 1)
        assert len(logs) == 5
        assert [l["step"] for l in logs] == [1, 2, 3, 4, 5]
