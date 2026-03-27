// hotel-compare/page-agent-version/background.js
/**
 * 酒店比价 — Background Service Worker
 * ======================================
 * 核心流程:
 *   popup 发送 START_COMPARE
 *   → background 依次打开 3 个标签页
 *   → 每个标签页注入 content.js
 *   → content.js 中的 page-agent 执行搜索
 *   → 结果回传给 popup
 *
 * Supabase 集成:
 *   - 创建 task 记录 (engine='page-agent')
 *   - 每个平台搜索完成后插入 result 行
 *   - 转发 agent activity 事件为 step_logs
 *   - 每 10s 轮询 pending 的 page-agent/dual 任务
 *   - 捕获标签页截图上传到 Supabase Storage
 */

import {
  supabaseInsert,
  supabaseFetch,
  supabaseUpdate,
  supabaseUploadScreenshot,
  isSupabaseConfigured,
} from './supabase-bridge.js';

// ---------------------------------------------------------------------------
// Platform definitions
// ---------------------------------------------------------------------------

const PLATFORMS = [
  {
    name: '携程',
    url: 'https://www.trip.com/hotels/',
    buildTask: (hotel, checkin, checkout) =>
      `在这个页面搜索酒店"${hotel}"，入住日期${checkin}，离店日期${checkout}。找到最匹配的酒店，告诉我最低价格和房型名称。用JSON格式回复：{"price": 数字, "roomType": "房型名", "hotelName": "酒店名"}`,
  },
  {
    name: '去哪儿',
    url: 'https://hotel.qunar.com/',
    buildTask: (hotel, checkin, checkout) =>
      `在这个页面搜索酒店"${hotel}"，入住日期${checkin}，离店日期${checkout}。找到最匹配的酒店，告诉我最低价格和房型名称。用JSON格式回复：{"price": 数字, "roomType": "房型名", "hotelName": "酒店名"}`,
  },
  {
    name: '同程',
    url: 'https://hotel.ly.com/',
    buildTask: (hotel, checkin, checkout) =>
      `在这个页面搜索酒店"${hotel}"，入住日期${checkin}，离店日期${checkout}。找到最匹配的酒店，告诉我最低价格和房型名称。用JSON格式回复：{"price": 数字, "roomType": "房型名", "hotelName": "酒店名"}`,
  },
];

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let pendingResults = {};
let completedCount = 0;
let totalPlatforms = 0;
/** Current Supabase task id (null if Supabase not configured) */
let currentTaskId = null;
/** Tracks start time per platform for duration calculation */
let platformStartTimes = {};

// ---------------------------------------------------------------------------
// Message listener
// ---------------------------------------------------------------------------

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'START_COMPARE') {
    runComparison(msg.hotel, msg.checkin, msg.checkout, msg.task_id);
  }
  if (msg.type === 'AGENT_RESULT') {
    handleAgentResult(sender.tab?.id, msg.result);
  }
  if (msg.type === 'AGENT_LOG') {
    broadcast({ type: 'LOG', text: `[${msg.platform}] ${msg.text}` });
  }
  if (msg.type === 'AGENT_STEP') {
    handleAgentStep(msg);
  }
});

// ---------------------------------------------------------------------------
// Core comparison flow
// ---------------------------------------------------------------------------

async function runComparison(hotel, checkin, checkout, externalTaskId) {
  pendingResults = {};
  completedCount = 0;
  totalPlatforms = PLATFORMS.length;
  currentTaskId = null;
  platformStartTimes = {};

  // Create or reuse a Supabase task
  if (await isSupabaseConfigured()) {
    try {
      if (externalTaskId) {
        // Reuse the provided task id (e.g. from dual-engine web UI)
        currentTaskId = externalTaskId;
        await supabaseUpdate('tasks', currentTaskId, { status: 'running' });
      } else {
        // Create a new task
        const task = await supabaseInsert('tasks', {
          hotel,
          checkin,
          checkout,
          status: 'running',
          engine: 'page-agent',
        });
        currentTaskId = task.id;
      }
      console.log('[supabase] task id:', currentTaskId);
    } catch (err) {
      console.warn('[supabase] Failed to create/update task:', err.message);
    }
  }

  for (const platform of PLATFORMS) {
    broadcast({
      type: 'PROGRESS',
      platform: platform.name,
      status: '正在打开页面...',
    });

    try {
      const tab = await chrome.tabs.create({ url: platform.url, active: false });
      await waitForTabLoad(tab.id);

      const task = platform.buildTask(hotel, checkin, checkout);
      chrome.tabs.sendMessage(tab.id, {
        type: 'RUN_AGENT',
        task,
        platform: platform.name,
      });

      pendingResults[tab.id] = { platform: platform.name, tabId: tab.id };
      platformStartTimes[platform.name] = Date.now();

      broadcast({
        type: 'PROGRESS',
        platform: platform.name,
        status: 'Agent 搜索中...',
      });

      // Capture initial screenshot
      await captureAndUploadScreenshot(tab.id, platform.name, 0);
    } catch (err) {
      broadcast({
        type: 'PROGRESS',
        platform: platform.name,
        status: `失败: ${err.message}`,
      });
      completedCount++;
      checkAllDone();
    }
  }
}

// ---------------------------------------------------------------------------
// Handle agent result from content script
// ---------------------------------------------------------------------------

async function handleAgentResult(tabId, result) {
  const info = pendingResults[tabId];
  if (!info) return;

  info.result = result;
  completedCount++;

  // Capture final screenshot
  await captureAndUploadScreenshot(tabId, info.platform, 'final');

  if (result && result.success) {
    try {
      const data = JSON.parse(result.data);
      broadcast({
        type: 'PROGRESS',
        platform: info.platform,
        status: '完成',
        data: { price: data.price, roomType: data.roomType },
      });
      info.parsed = data;

      // Persist result to Supabase
      await persistResult(info.platform, data, null);
    } catch {
      broadcast({
        type: 'PROGRESS',
        platform: info.platform,
        status: '结果解析失败',
      });
      await persistResult(info.platform, null, 'JSON parse failed');
    }
  } else {
    broadcast({
      type: 'PROGRESS',
      platform: info.platform,
      status: '搜索失败',
    });
    await persistResult(info.platform, null, result?.data || 'Unknown error');
  }

  checkAllDone();
}

// ---------------------------------------------------------------------------
// Handle structured agent step from content script
// ---------------------------------------------------------------------------

async function handleAgentStep(step) {
  // Forward as a log to popup
  const logText = `[${step.platform}] Step ${step.stepNum}: ${step.goal || ''} — ${(step.actions || []).join(', ')}`;
  broadcast({ type: 'LOG', text: logText });

  // Persist to Supabase step_logs
  if (currentTaskId && (await isSupabaseConfigured())) {
    try {
      await supabaseInsert('step_logs', {
        task_id: currentTaskId,
        platform: step.platform,
        step_num: step.stepNum,
        goal: step.goal || null,
        actions: step.actions ? JSON.stringify(step.actions) : null,
        url: step.url || null,
        engine: 'page-agent',
      });
    } catch (err) {
      console.warn('[supabase] Failed to insert step_log:', err.message);
    }
  }
}

// ---------------------------------------------------------------------------
// Persist a result row to Supabase
// ---------------------------------------------------------------------------

async function persistResult(platform, parsedData, errorMsg) {
  if (!currentTaskId || !(await isSupabaseConfigured())) return;

  const durationMs = platformStartTimes[platform]
    ? Date.now() - platformStartTimes[platform]
    : null;

  try {
    await supabaseInsert('results', {
      task_id: currentTaskId,
      platform,
      hotel_name: parsedData?.hotelName || null,
      lowest_price: parsedData?.price || null,
      room_type: parsedData?.roomType || null,
      error: errorMsg || null,
      engine: 'page-agent',
      duration_seconds: durationMs ? durationMs / 1000 : null,
    });
  } catch (err) {
    console.warn('[supabase] Failed to insert result:', err.message);
  }
}

// ---------------------------------------------------------------------------
// Screenshot capture & upload
// ---------------------------------------------------------------------------

async function captureAndUploadScreenshot(tabId, platform, stepOrLabel) {
  if (!currentTaskId || !(await isSupabaseConfigured())) return null;

  try {
    // chrome.tabs.captureVisibleTab requires the tab to be in the active window
    // We capture the tab's window
    const tab = await chrome.tabs.get(tabId);
    const dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, {
      format: 'png',
    });

    // Strip the data:image/png;base64, prefix
    const base64Data = dataUrl.replace(/^data:image\/png;base64,/, '');
    const path = `${currentTaskId}/${platform}-step-${stepOrLabel}.png`;

    const { publicUrl } = await supabaseUploadScreenshot(path, base64Data);

    // If we have a step_log for this, we could update it — for now just log
    console.log('[supabase] Screenshot uploaded:', publicUrl);
    return publicUrl;
  } catch (err) {
    // captureVisibleTab can fail if tab is not visible — that is expected
    console.warn('[supabase] Screenshot capture failed:', err.message);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Completion check
// ---------------------------------------------------------------------------

async function checkAllDone() {
  if (completedCount < totalPlatforms) return;

  const results = Object.values(pendingResults).map((info) => {
    if (info.parsed) {
      return {
        platform: info.platform,
        price: info.parsed.price,
        roomType: info.parsed.roomType,
        hotelName: info.parsed.hotelName,
      };
    }
    return null;
  });

  broadcast({ type: 'COMPLETE', results });

  // Update Supabase task status
  if (currentTaskId && (await isSupabaseConfigured())) {
    const hasSuccess = results.some((r) => r !== null);
    try {
      await supabaseUpdate('tasks', currentTaskId, {
        status: hasSuccess ? 'completed' : 'failed',
      });
    } catch (err) {
      console.warn('[supabase] Failed to update task status:', err.message);
    }
  }
}

// ---------------------------------------------------------------------------
// Tab load helper
// ---------------------------------------------------------------------------

function waitForTabLoad(tabId) {
  return new Promise((resolve) => {
    function listener(updatedTabId, changeInfo) {
      if (updatedTabId === tabId && changeInfo.status === 'complete') {
        chrome.tabs.onUpdated.removeListener(listener);
        setTimeout(resolve, 2000);
      }
    }
    chrome.tabs.onUpdated.addListener(listener);
  });
}

// ---------------------------------------------------------------------------
// Broadcast to popup
// ---------------------------------------------------------------------------

function broadcast(msg) {
  chrome.runtime.sendMessage(msg).catch(() => {
    // popup 可能已关闭，忽略错误
  });
}

// ---------------------------------------------------------------------------
// Supabase polling — check for pending tasks every 10 seconds
// ---------------------------------------------------------------------------

const POLL_INTERVAL_MS = 10_000;

async function pollPendingTasks() {
  if (!(await isSupabaseConfigured())) return;

  try {
    const tasks = await supabaseFetch('tasks', {
      status: 'eq.pending',
      engine: 'in.(page-agent,dual)',
      order: 'created_at.asc',
      limit: 1,
    });

    if (tasks.length > 0) {
      const task = tasks[0];
      console.log('[supabase] Found pending task:', task.id);
      runComparison(task.hotel, task.checkin, task.checkout, task.id);
    }
  } catch (err) {
    console.warn('[supabase] Polling error:', err.message);
  }
}

// Start polling loop via setInterval (service worker will stay alive while active)
setInterval(pollPendingTasks, POLL_INTERVAL_MS);

// Also run once on startup
pollPendingTasks();
