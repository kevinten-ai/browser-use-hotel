"""Tests for supabase_client.py with mocked Supabase client.

Validates that the correct data shapes are sent to Supabase,
especially the new fields added by migrations 002-005.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestInsertStepLog:
    def test_required_fields_only(self):
        with patch("supabase_client.get_client") as mock_gc:
            mock_table = MagicMock()
            mock_gc.return_value.table.return_value = mock_table
            mock_table.insert.return_value.execute.return_value = None

            from supabase_client import insert_step_log
            insert_step_log("task-1", "携程", 1, "点击搜索", "https://img.png")

            mock_table.insert.assert_called_once()
            row = mock_table.insert.call_args[0][0]
            assert row["task_id"] == "task-1"
            assert row["platform"] == "携程"
            assert row["step_num"] == 1
            assert row["goal"] == "点击搜索"
            assert "thinking" not in row
            assert "evaluation" not in row

    def test_with_rich_fields(self):
        with patch("supabase_client.get_client") as mock_gc:
            mock_table = MagicMock()
            mock_gc.return_value.table.return_value = mock_table
            mock_table.insert.return_value.execute.return_value = None

            from supabase_client import insert_step_log
            insert_step_log(
                "task-1", "携程", 1, "目标", "",
                thinking="我在思考",
                evaluation="上一步成功",
                memory="记住了搜索框位置",
                actions=[{"click": {"index": 42}}],
                url="https://ctrip.com",
            )

            row = mock_table.insert.call_args[0][0]
            assert row["thinking"] == "我在思考"
            assert row["evaluation"] == "上一步成功"
            assert row["memory"] == "记住了搜索框位置"
            assert row["actions"] == [{"click": {"index": 42}}]
            assert row["url"] == "https://ctrip.com"


class TestInsertResult:
    def test_success_result(self):
        with patch("supabase_client.get_client") as mock_gc:
            mock_table = MagicMock()
            mock_gc.return_value.table.return_value = mock_table
            mock_table.insert.return_value.execute.return_value = None

            from supabase_client import insert_result
            insert_result(
                "task-1", "携程",
                hotel_name="北京国贸", lowest_price=888,
                room_type="大床房", page_url="https://ctrip.com/123",
                strategy_name="desktop", attempt_number=1,
            )

            row = mock_table.insert.call_args[0][0]
            assert row["hotel_name"] == "北京国贸"
            assert row["lowest_price"] == 888
            assert row["strategy_name"] == "desktop"
            assert row["attempt_number"] == 1
            assert row["error"] is None

    def test_error_result(self):
        with patch("supabase_client.get_client") as mock_gc:
            mock_table = MagicMock()
            mock_gc.return_value.table.return_value = mock_table
            mock_table.insert.return_value.execute.return_value = None

            from supabase_client import insert_result
            insert_result("task-1", "去哪儿", error="All strategies exhausted")

            row = mock_table.insert.call_args[0][0]
            assert row["error"] == "All strategies exhausted"
            assert row["hotel_name"] is None

    def test_optional_fields_excluded_when_none(self):
        with patch("supabase_client.get_client") as mock_gc:
            mock_table = MagicMock()
            mock_gc.return_value.table.return_value = mock_table
            mock_table.insert.return_value.execute.return_value = None

            from supabase_client import insert_result
            insert_result("task-1", "同程")

            row = mock_table.insert.call_args[0][0]
            assert "strategy_name" not in row
            assert "attempt_number" not in row
