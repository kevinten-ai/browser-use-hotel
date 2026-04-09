# Midscene.js 深度调研

## 一、项目概览

Midscene.js 是字节跳动 Web Infra 团队开源的 AI 驱动视觉化 UI 自动化框架。

- **GitHub Stars**：12,208
- **最新版本**：v1.5.6（2026-03-17）
- **语言**：TypeScript
- **许可证**：MIT

### 近期更新

| 版本 | 日期 | 主要更新 |
|------|------|----------|
| v1.5.6 | 2026-03-17 | 新增 Codex app-server provider |
| v1.5.5 | 2026-03-16 | GPT-5.4 模型兼容 |
| v1.5.3 | 2026-03-09 | 设备感知渲染、AI 调用计时 |
| v1.5.0 | 2026-03-02 | @midscene/harmony（HarmonyOS）、deepThink 子目标规划 |

---

## 二、核心设计哲学：纯视觉驱动

v1.0+ 全面采用**纯视觉（Pure Vision）**路线，彻底放弃 DOM 提取：
- **跨平台通用**：Web/Android/iOS/桌面/HarmonyOS 均可支持
- **Token 消耗降低约 80%**
- 依赖多模态大模型的视觉理解能力

### 三层推理架构

```
任务规划层 → 将自然语言指令转化为操作序列
语义理解层 → 构建 UI 元素关系图谱
视觉特征层 → 处理屏幕像素，识别 UI 元素
```

---

## 三、核心 API

### 3.1 aiAct() — 自然语言操作

```typescript
await agent.ai('在搜索框中输入"Midscene"，然后点击搜索按钮');
```

内部流程：截图 → 规划模型分析 → 返回操作序列 → 逐步执行（每步重新截图定位）

### 3.2 aiQuery() — 数据提取

```typescript
const items = await agent.aiQuery<string[]>('获取所有商品名称列表');
const data = await agent.aiQuery({
  productName: 'string, 商品名称',
  price: 'number, 价格',
});
```

### 3.3 aiAssert() — 视觉断言

```typescript
await agent.aiAssert('页面上显示了登录成功的提示');
await agent.aiAssert('价格应该在100元左右'); // 支持模糊断言
```

### 3.4 即时操作 — 速度提升 3-10 倍

```typescript
await agent.aiTap('登录按钮');
await agent.aiInput('搜索框', 'Midscene');
await agent.aiScroll('down');
```

跳过规划步骤，直接执行。

---

## 四、多模型策略

| 模型角色 | 用途 | 推荐模型 |
|----------|------|----------|
| 默认模型 | 元素定位 + 未分配任务 | Qwen3-VL |
| 规划模型 | aiAct 任务规划 | GPT-5.4 / 豆包 Seed |
| 洞察模型 | aiQuery/aiAssert 数据理解 | 通义千问 3.5 |

---

## 五、与 Playwright 集成

```typescript
import { chromium } from 'playwright';
import { PlaywrightAgent } from '@midscene/web';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
const agent = new PlaywrightAgent(page);

await agent.aiAct('在搜索框输入 Midscene');
const results = await agent.aiQuery<string[]>('搜索结果标题列表');
await agent.aiAssert('搜索结果不为空');
```

---

## 六、包结构（Monorepo）

- `@midscene/core` — 核心逻辑
- `@midscene/web-integration` — Playwright/Puppeteer 集成
- `@midscene/android` — Android 自动化（adb）
- `@midscene/ios` — iOS 自动化（WebDriverAgent）
- `@midscene/harmony` — HarmonyOS 自动化
- `@midscene/cli` — 命令行工具
- `@midscene/visualizer` — 可视化报告
- `@midscene/mcp` — MCP 服务器集成

---

## 七、与传统选择器方式对比

| 维度 | 传统选择器 | Midscene |
|------|-----------|----------|
| 元素定位 | CSS/XPath/data-testid | 自然语言 + 视觉定位 |
| 脆弱性 | DOM 变更即失效 | UI 语义不变即可工作 |
| 维护成本 | 高 | 减少约 80% |
| 跨平台 | 每平台不同工具 | 统一 SDK |
| 执行速度 | 毫秒级 | 慢 3-10 倍 |
| 成本 | 免费 | 需 LLM API 费用 |

---

## 八、缓存机制

- **指令缓存**：以 prompt 为键存储执行计划
- **定位缓存**：存储元素 XPath，下次验证有效性
- **效果**：执行时间从 1分16秒 → 23秒

---

## 九、已知限制

1. 执行速度慢 3-10 倍
2. 不支持多标签页
3. AI 非 100% 稳定
4. 无法分析 iframe 内容
5. 敏感信息无法隐藏
6. 无障碍验证缺失
7. 持续的 LLM API 调用成本

---

## 十、与 browser-use 的关键区别

| 维度 | Midscene | browser-use |
|------|----------|-------------|
| 定位 | UI 测试自动化框架 | 通用任务自动化 Agent |
| 语言 | TypeScript | Python |
| 感知方式 | 纯视觉（v1.0+） | DOM + 视觉混合 |
| API 风格 | 细粒度（aiTap/aiQuery/aiAssert） | 高层 Agent 抽象 |
| 跨平台 | Web/Android/iOS/桌面/HarmonyOS | 仅浏览器 |
| 自纠错 | 无（靠缓存和重试） | 内置反思和重试 |
| 生态集成 | Playwright/Puppeteer 原生集成 | LangChain 生态 |
