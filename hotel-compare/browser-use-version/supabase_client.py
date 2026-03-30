"""Supabase client — 封装数据库和存储操作"""

import os
import base64
from supabase import create_client

_client = None

def get_client():
    global _client
    if _client is None:
        _client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_KEY"],
        )
    return _client

def create_task(hotel: str, checkin: str, checkout: str) -> str:
    """创建搜索任务，返回 task_id"""
    resp = get_client().table("tasks").insert({
        "hotel": hotel,
        "checkin": checkin,
        "checkout": checkout,
        "status": "pending",
    }).execute()
    return resp.data[0]["id"]

def update_task_status(task_id: str, status: str):
    get_client().table("tasks").update({"status": status}).eq("id", task_id).execute()

def fetch_pending_task():
    """获取一个 pending 任务并标记为 running"""
    resp = (
        get_client()
        .table("tasks")
        .select("*")
        .eq("status", "pending")
        .order("created_at")
        .limit(1)
        .execute()
    )
    if not resp.data:
        return None
    task = resp.data[0]
    update_task_status(task["id"], "running")
    return task

def upload_screenshot(task_id: str, platform: str, step_num: int, screenshot_b64: str) -> str:
    """上传 base64 截图到 Supabase Storage，返回公开 URL"""
    path = f"{task_id}/{platform}_{step_num}.png"
    file_bytes = base64.b64decode(screenshot_b64)
    get_client().storage.from_("screenshots").upload(
        path, file_bytes, {"content-type": "image/png"}
    )
    return get_client().storage.from_("screenshots").get_public_url(path)

def insert_step_log(task_id: str, platform: str, step_num: int, goal: str, screenshot_url: str,
                    thinking: str = None, evaluation: str = None, memory: str = None,
                    actions=None, plan=None, url: str = None):
    row = {
        "task_id": task_id,
        "platform": platform,
        "step_num": step_num,
        "goal": goal,
        "screenshot_url": screenshot_url,
    }
    if thinking is not None: row["thinking"] = thinking
    if evaluation is not None: row["evaluation"] = evaluation
    if memory is not None: row["memory"] = memory
    if actions is not None: row["actions"] = actions
    if plan is not None: row["plan"] = plan
    if url is not None: row["url"] = url
    get_client().table("step_logs").insert(row).execute()

def insert_result(task_id: str, platform: str, hotel_name: str = None,
                  lowest_price: float = None, room_type: str = None,
                  page_url: str = None, error: str = None,
                  strategy_name: str = None, attempt_number: int = None):
    row = {
        "task_id": task_id,
        "platform": platform,
        "hotel_name": hotel_name,
        "lowest_price": lowest_price,
        "room_type": room_type,
        "page_url": page_url,
        "error": error,
    }
    if strategy_name is not None: row["strategy_name"] = strategy_name
    if attempt_number is not None: row["attempt_number"] = attempt_number
    get_client().table("results").insert(row).execute()
