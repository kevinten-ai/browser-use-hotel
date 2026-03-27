"""Worker — 轮询 Supabase 任务队列，执行 browser-use 搜索"""

import asyncio
import time
from dotenv import load_dotenv

load_dotenv()

from supabase_client import fetch_pending_task, update_task_status, insert_result
from platform_config import ALL_PLATFORMS
from retry_strategies import search_with_retry


async def process_task(task: dict):
    """处理一个搜索任务"""
    task_id = task["id"]
    hotel = task["hotel"]
    checkin = task["checkin"]
    checkout = task["checkout"]
    print(f"\n{'='*50}")
    print(f"Processing: {hotel} | {checkin} → {checkout}")
    print(f"Task ID: {task_id}")

    logs = []
    for config in ALL_PLATFORMS:
        print(f"\n  Searching {config.name}...")
        try:
            result = await search_with_retry(
                config, hotel, checkin, checkout, logs, task_id=task_id,
            )
            if result:
                insert_result(
                    task_id, config.name,
                    hotel_name=result.hotel_name,
                    lowest_price=result.lowest_price,
                    room_type=result.room_type,
                    page_url=result.url,
                    strategy_name=getattr(result, '_strategy_name', None),
                    attempt_number=getattr(result, '_attempt_number', None),
                )
                print(f"  {config.name}: ¥{result.lowest_price:.0f} {result.room_type}")
            else:
                insert_result(task_id, config.name, error="All strategies exhausted")
                print(f"  {config.name}: No result (all strategies exhausted)")
        except Exception as e:
            insert_result(task_id, config.name, error=str(e))
            print(f"  {config.name}: Error - {e}")

    update_task_status(task_id, "completed")
    print(f"\nTask {task_id} completed.")


def poll_loop():
    """主循环：每 5 秒检查一次新任务"""
    print("Worker started. Polling for tasks...")
    while True:
        task = fetch_pending_task()
        if task:
            asyncio.run(process_task(task))
        else:
            time.sleep(5)


if __name__ == "__main__":
    poll_loop()
