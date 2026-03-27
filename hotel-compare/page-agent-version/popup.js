// hotel-compare/page-agent-version/popup.js
/**
 * 酒店比价 Chrome 扩展 — popup 控制逻辑
 * ============================================
 * 📚 学习点:
 *   1. Chrome Extension popup 与 background 通信
 *   2. chrome.runtime.sendMessage / onMessage 消息机制
 *   3. 实时更新 UI 的模式
 */

// 初始化日期默认值
const today = new Date();
const checkinDate = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
const checkoutDate = new Date(today.getTime() + 9 * 24 * 60 * 60 * 1000);
document.getElementById('checkin').value = checkinDate.toISOString().split('T')[0];
document.getElementById('checkout').value = checkoutDate.toISOString().split('T')[0];

// 监听来自 background 的进度更新
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'PROGRESS') {
    updatePlatformStatus(msg.platform, msg.status, msg.data);
  }
  if (msg.type === 'LOG') {
    addLog(msg.text);
  }
  if (msg.type === 'COMPLETE') {
    onComplete(msg.results);
  }
});

// 绑定按钮点击事件
document.getElementById('startBtn').addEventListener('click', startCompare);

async function startCompare() {
  const hotel = document.getElementById('hotel').value.trim();
  const checkin = document.getElementById('checkin').value;
  const checkout = document.getElementById('checkout').value;

  if (!hotel || !checkin || !checkout) {
    alert('请填写完整信息');
    return;
  }

  // 显示状态区域
  document.getElementById('statusSection').classList.remove('hidden');
  document.getElementById('logSection').classList.remove('hidden');
  document.getElementById('resultBox').classList.add('hidden');
  document.getElementById('startBtn').disabled = true;
  document.getElementById('startBtn').textContent = '🔄 搜索中...';

  // 重置状态
  ['ctrip', 'qunar', 'tongcheng'].forEach(id => {
    document.getElementById(id + 'Status').textContent = '⏳ 等待中';
    document.getElementById(id + 'Price').textContent = '';
    document.getElementById(id + 'Row').classList.remove('platform-best');
  });

  // 发送任务到 background
  chrome.runtime.sendMessage({
    type: 'START_COMPARE',
    hotel,
    checkin,
    checkout,
  });
}

function updatePlatformStatus(platform, status, data) {
  const idMap = { '携程': 'ctrip', '去哪儿': 'qunar', '同程': 'tongcheng' };
  const id = idMap[platform];
  if (!id) return;

  document.getElementById(id + 'Status').textContent = status;
  if (data && data.price) {
    document.getElementById(id + 'Price').textContent = `¥${data.price}`;
  }
}

function addLog(text) {
  const logSection = document.getElementById('logSection');
  const entry = document.createElement('div');
  entry.className = 'log-entry';
  entry.textContent = text;
  logSection.appendChild(entry);
  logSection.scrollTop = logSection.scrollHeight;
}

function onComplete(results) {
  document.getElementById('startBtn').disabled = false;
  document.getElementById('startBtn').textContent = '🔍 开始比价';

  const valid = results.filter(r => r && r.price);
  if (valid.length === 0) {
    document.getElementById('resultBox').classList.remove('hidden');
    document.getElementById('bestPrice').textContent = '搜索失败';
    document.getElementById('bestPlatform').textContent = '请重试';
    return;
  }

  valid.sort((a, b) => a.price - b.price);
  const best = valid[0];

  // 高亮最低价平台
  const idMap = { '携程': 'ctrip', '去哪儿': 'qunar', '同程': 'tongcheng' };
  const bestId = idMap[best.platform];
  if (bestId) {
    document.getElementById(bestId + 'Row').classList.add('platform-best');
  }

  // 显示结果
  document.getElementById('resultBox').classList.remove('hidden');
  document.getElementById('bestPrice').textContent = `¥${best.price}`;
  document.getElementById('bestPlatform').textContent = `${best.platform} · ${best.roomType}`;
}
