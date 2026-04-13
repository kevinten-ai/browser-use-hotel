"""Worker — 轮询 Supabase 任务队列，串行执行 browser-use 搜索

注意：Railway 小容器（512MB-1GB RAM）无法同时运行 3 个 headless Chromium 实例，
并行会导致 CDP 连接超时。所以这里用串行，每次只开 1 个浏览器。
"""

import asyncio
import time
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from supabase_client import fetch_pending_task, update_task_status, insert_result, SupabaseError
from platform_config import ALL_PLATFORMS
from retry_strategies import search_with_retry


POLL_INTERVAL_SECONDS: float = 5.0


async def process_task(task: dict[str, Any]) -> None:
    """串行处理三个平台的搜索任务"""
    task_id = task["id"]
    hotel = task["hotel"]
    checkin = task["checkin"]
    checkout = task["checkout"]
    print(f"\n{'=' * 50}")
    print(f"Processing: {hotel} | {checkin} → {checkout}")
    print(f"Task ID: {task_id}")

    for config in ALL_PLATFORMS:
        print(f"\n  --- Searching {config.name} ---")
        logs: list[dict[str, Any]] = []
        start_time = time.time()
        try:
            result = await search_with_retry(
                config, hotel, checkin, checkout, logs, task_id=task_id,
            )
            duration = time.time() - start_time
            if result:
                insert_result(
                    task_id, config.name,
                    hotel_name=result.hotel_name,
                    lowest_price=result.lowest_price,
                    room_type=result.room_type,
                    page_url=result.url,
                    strategy_name=getattr(result, "_strategy_name", None),
                    attempt_number=getattr(result, "_attempt_number", None),
                    duration_seconds=duration,
                    engine="browser-use",
                )
                print(f"  {config.name}: ¥{result.lowest_price:.0f} {result.room_type}")
            else:
                insert_result(
                    task_id, config.name,
                    error="All strategies exhausted",
                    duration_seconds=duration,
                    engine="browser-use",
                )
                print(f"  {config.name}: No result (all strategies exhausted)")
        except Exception as exc:
            duration = time.time() - start_time
            insert_result(
                task_id, config.name,
                error=str(exc),
                duration_seconds=duration,
                engine="browser-use",
            )
            print(f"  {config.name}: Error - {exc}")

    try:
        update_task_status(task_id, "completed")
    except SupabaseError as exc:
        print(f"  [worker] Failed to mark task {task_id} completed: {exc}")
    print(f"\nTask {task_id} completed.")


async def poll_loop_async() -> None:
    """主循环：每 5 秒检查一次新任务"""
    print("Worker started. Polling for tasks...")
    while True:
        try:
            task = fetch_pending_task()
        except SupabaseError as exc:
            print(f"  [worker] Failed to fetch pending task: {exc}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            continue

        if task:
            await process_task(task)
        else:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


def poll_loop() -> None:
    asyncio.run(poll_loop_async())


if __name__ == "__main__":
    poll_loop()
