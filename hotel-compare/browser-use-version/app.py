"""
酒店跨平台比价 — Streamlit 可视化界面
======================================
学习目标：
  1. 用 Streamlit 快速搭建可视化界面
  2. 将 browser-use 的执行过程实时展示给用户
  3. 理解 Agent 回调函数如何与 UI 联动
"""

import asyncio
import time
from datetime import date, timedelta
from typing import Any

import streamlit as st

from hotel_compare import HotelPrice, search_ctrip, search_qunar, search_tongcheng


def _run_async(coro):
    """在 Streamlit 环境中安全运行异步协程。

    Streamlit 的脚本执行器运行在工作线程，部分环境下已有 event loop，
    直接使用 asyncio.run() 可能抛出 RuntimeError。此 helper 兼容两种场景。
    """
    try:
        return asyncio.run(coro)
    except RuntimeError as exc:
        if "cannot be called from a running event loop" in str(exc):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        raise


st.set_page_config(page_title="🏨 酒店跨平台比价", layout="wide")
st.title("🏨 酒店跨平台比价工具")
st.caption("基于 browser-use Agent — 服务端浏览器自动化方案")

# ── 输入区域 ──
col1, col2, col3 = st.columns(3)
with col1:
    hotel = st.text_input("酒店名称", value="北京国贸大酒店")
with col2:
    checkin = st.date_input("入住日期", value=date.today() + timedelta(days=7))
with col3:
    checkout = st.date_input("离店日期", value=date.today() + timedelta(days=9))

start_btn = st.button("🔍 开始比价", type="primary", use_container_width=True)

if start_btn:
    if not hotel:
        st.error("请输入酒店名称")
        st.stop()

    checkin_str = checkin.strftime("%Y-%m-%d")
    checkout_str = checkout.strftime("%Y-%m-%d")
    nights = (checkout - checkin).days

    st.markdown(f"**{hotel}** | {checkin_str} → {checkout_str} ({nights}晚)")
    st.divider()

    # ── 执行进度区域 ──
    logs: list[dict[str, Any]] = []
    results: list[HotelPrice | None] = []

    platforms: list[tuple[str, str, Any]] = [
        ("携程", "trip.com", search_ctrip),
        ("去哪儿", "qunar.com", search_qunar),
        ("同程", "ly.com", search_tongcheng),
    ]

    progress = st.progress(0, text="准备中...")
    status_cols = st.columns(3)

    # 为每个平台创建状态展示区
    platform_containers: dict[str, Any] = {}
    for i, (name, _domain, _) in enumerate(platforms):
        with status_cols[i]:
            platform_containers[name] = st.container(border=True)
            platform_containers[name].markdown(f"### {name}\n⏳ 等待中")

    # ── 日志区域 ──
    log_expander = st.expander("📋 Agent 执行日志", expanded=True)

    # ── 顺序执行搜索 ──
    for idx, (name, _domain, search_fn) in enumerate(platforms):
        progress.progress(
            idx / len(platforms),
            text=f"正在搜索 {name}..."
        )
        platform_containers[name].markdown(f"### {name}\n🔄 正在搜索...")

        start_time = time.time()
        result = _run_async(search_fn(hotel, checkin_str, checkout_str, logs))
        elapsed = time.time() - start_time

        results.append(result)

        # 更新平台状态
        if result:
            platform_containers[name].markdown(
                f"### {name}\n"
                f"✅ 搜索完成 ({elapsed:.0f}s)\n\n"
                f"**¥{result.lowest_price:.0f}** {result.room_type}"
            )
        else:
            platform_containers[name].markdown(
                f"### {name}\n"
                f"❌ 搜索失败 ({elapsed:.0f}s)"
            )

        # 更新日志
        platform_logs = [entry for entry in logs if entry["platform"] == name]
        with log_expander:
            for log in platform_logs:
                st.text(f"[{log['platform']}] Step {log['step']}: {log['goal']}")

    progress.progress(1.0, text="完成!")

    # ── 对比结果表格 ──
    st.divider()
    st.subheader("📊 对比结果")

    valid_results = [r for r in results if r is not None]
    if valid_results:
        valid_results.sort(key=lambda x: x.lowest_price)

        table_data = []
        for i, r in enumerate(valid_results):
            table_data.append({
                "排名": f"{'🏆 ' if i == 0 else ''}{i+1}",
                "平台": r.platform,
                "最低价": f"¥{r.lowest_price:.0f}",
                "房型": r.room_type,
                "链接": r.url,
            })

        st.table(table_data)

        if len(valid_results) >= 2:
            diff = valid_results[-1].lowest_price - valid_results[0].lowest_price
            st.success(
                f"💰 最低价: **{valid_results[0].platform} ¥{valid_results[0].lowest_price:.0f}** "
                f"(比最高价低 ¥{diff:.0f})"
            )
    else:
        st.error("所有平台搜索均失败，请检查网络或重试")

    # ── 执行统计 ──
    st.divider()
    st.subheader("📈 执行统计")
    stat_cols = st.columns(3)
    stat_cols[0].metric("总步数", f"{len(logs)} 步")
    stat_cols[1].metric("成功平台", f"{len(valid_results)}/3")
    stat_cols[2].metric("日志条数", f"{len(logs)} 条")
