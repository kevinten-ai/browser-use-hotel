# BrowserAgent 培训大纲

## 培训概览

本培训聚焦于基于 GUI 的浏览器智能体（BrowserAgent）技术，涵盖基本原理、架构设计、实战开发和效果评测优化。

---

## 课程一：GUI 基本原理与架构

**形式**: 在线学习（课前预习）
**要求**: 讲师提供相关学习链接（不限内外网），学员课前需全部掌握

### 预习资料

| 资料 | 链接 | 说明 |
|------|------|------|
| browser-use | https://github.com/browser-use/browser-use | 基于 LLM 的浏览器自动化框架 |
| Midscene | https://github.com/web-infra-dev/midscene | 基于 AI 的 UI 自动化测试框架 |
| MobileAgent | https://github.com/X-PLUG/MobileAgent | 移动端多模态 Agent |
| Playwright (Python) | https://playwright.dev/python/ | 浏览器自动化测试框架 |

---

## 课程二（Workshop 2）：实现基于 Chrome 的 BrowserAgent

**形式**: 线下实战

### 核心目标
- 设计并实现一个基于 Chrome 浏览器的 BrowserAgent
- 结合 LLM 能力实现网页交互自动化
- 理解 GUI Agent 的感知-决策-执行循环

---

## 课程三（Workshop 3）：BrowserAgent 评测以及效果优化

**形式**: 总结与交流

### 核心目标
- 建立 BrowserAgent 的评测体系
- 分析常见问题与优化策略
- 经验总结与最佳实践分享

---

## 关键技术栈

### 1. browser-use

browser-use 是一个将 AI Agent 连接到浏览器的开源框架，让 LLM 能够像人类一样操作浏览器完成各种任务。

**核心特性**:
- 视觉 + HTML 混合感知：结合截图和 DOM 信息理解页面
- 多标签页管理：支持跨标签页操作
- 自定义 Action 注册：可以扩展 Agent 的能力
- 支持多种 LLM（GPT-4o、Claude、Gemini 等）
- 自动处理 Cookie 弹窗等常见干扰
- 支持自主纠错和重试

**架构概览**:
```
User Task (自然语言)
      ↓
   LLM (规划 + 决策)
      ↓
  browser-use Controller (动作执行)
      ↓
  Playwright (浏览器操作)
      ↓
  浏览器页面 (截图/DOM 反馈)
      ↓
   返回 LLM（感知-决策循环）
```

**核心组件**:
- **Agent**: 主控模块，管理任务执行循环
- **Browser**: 浏览器抽象层，基于 Playwright
- **Controller**: 注册和执行浏览器动作
- **DOM 提取器**: 将页面元素转化为 LLM 可理解的结构化信息

**基本使用示例**:
```python
from langchain_openai import ChatOpenAI
from browser_use import Agent

import asyncio

async def main():
    agent = Agent(
        task="Go to google.com and search for 'browser-use framework'",
        llm=ChatOpenAI(model="gpt-4o"),
    )
    result = await agent.run()
    print(result)

asyncio.run(main())
```

**关键设计理念**:
- **感知层**: 截图（视觉信息）+ DOM 提取（结构化信息）双通道感知
- **决策层**: LLM 基于当前页面状态和任务目标进行推理规划
- **执行层**: 将 LLM 决策转化为具体的浏览器操作（点击、输入、滚动等）
- **反馈层**: 执行后重新感知页面状态，形成闭环

---

### 2. Midscene

Midscene 是由字节跳动 Web Infra 团队开发的 AI 驱动的 UI 自动化框架。

**核心特性**:
- 用自然语言描述 UI 操作（如 "点击登录按钮"）
- AI 理解页面语义，自动定位元素
- 支持视觉断言（如 "检查页面是否显示成功消息"）
- 与 Playwright/Puppeteer 深度集成
- 支持数据提取（从页面中提取结构化数据）

**三大核心 API**:
- **ai()** / **aiAction()**: 通过自然语言执行页面操作
- **aiQuery()**: 从页面中提取和查询数据
- **aiAssert()**: AI 驱动的视觉断言

**使用示例**:
```typescript
import { ai, aiQuery } from "@midscene/web";

// 自然语言操作
await ai("在搜索框中输入 'AI automation'，然后点击搜索按钮");

// 数据提取
const results = await aiQuery("获取搜索结果列表中的所有标题");

// 视觉断言
await aiAssert("页面上显示了搜索结果");
```

**与 browser-use 的区别**:
- Midscene 更侧重于 **UI 测试自动化**，强调断言和验证
- browser-use 更侧重于 **通用任务自动化**，强调端到端任务完成
- Midscene 提供更细粒度的 API 控制
- browser-use 提供更高层的 Agent 抽象

---

### 3. MobileAgent (X-PLUG)

MobileAgent 是阿里巴巴达摩院开发的自主多模态移动端 Agent。

**核心特性**:
- 多模态感知：结合视觉（截图）和文本信息理解移动端界面
- 跨应用操作：可以在多个 App 之间切换完成任务
- 自主规划：基于任务目标自动规划操作步骤
- 自主反思：检测操作失误并自动纠错

**架构设计**:
- **视觉感知模块**: 截图分析 + OCR 文字识别 + 图标检测
- **规划模块**: 基于 LLM 的任务分解和步骤规划
- **执行模块**: 模拟触屏操作（点击、滑动、输入等）
- **反思模块**: 操作后验证结果，必要时回退和重试

**与桌面浏览器 Agent 的异同**:

| 维度 | BrowserAgent (桌面) | MobileAgent (移动端) |
|------|---------------------|---------------------|
| 感知方式 | DOM + 截图 | 截图 + OCR |
| 操作方式 | 鼠标/键盘 | 触屏手势 |
| 页面结构 | HTML DOM 可用 | 视图层级，可访问性信息 |
| 交互复杂度 | 较低 | 较高（手势多样性） |
| 跨应用 | 多标签页 | 多应用切换 |

---

### 4. Playwright (Python)

Playwright 是微软开发的跨浏览器自动化测试框架，是 BrowserAgent 的底层执行引擎。

**核心特性**:
- 支持 Chromium、Firefox、WebKit 三大浏览器引擎
- 自动等待元素就绪
- 网络拦截和修改
- 移动端设备模拟
- 截图和录屏
- 多页面/多上下文支持

**Python API 示例**:
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://example.com")

    # 元素定位与操作
    page.fill("input[name='search']", "browser agent")
    page.click("button[type='submit']")

    # 截图
    page.screenshot(path="screenshot.png")

    # 等待与断言
    page.wait_for_selector(".results")

    browser.close()
```

**在 BrowserAgent 中的角色**:
- 提供浏览器启动和管理
- 执行具体的页面操作（点击、输入、滚动等）
- 获取页面截图用于视觉感知
- 提取 DOM 信息用于结构化感知
- 处理网络请求和响应

---

## GUI Agent 核心原理

### 感知-决策-执行循环 (Perception-Decision-Action Loop)

```
┌──────────────────────────────────────────────┐
│                  GUI Agent                    │
│                                              │
│   ┌──────────┐    ┌──────────┐    ┌────────┐│
│   │  感知层   │───→│  决策层   │───→│ 执行层 ││
│   │Perception│    │ Decision │    │ Action ││
│   └────▲─────┘    └──────────┘    └───┬────┘│
│        │                              │      │
│        └──────────────────────────────┘      │
│              状态反馈 (Feedback)              │
└──────────────────────────────────────────────┘
```

### 1. 感知层 (Perception)

**视觉感知**:
- 页面截图 → 多模态 LLM 理解
- UI 元素检测和识别
- 页面布局和结构理解

**结构化感知**:
- DOM 树提取和简化
- 可交互元素标注（Set-of-Mark / Bounding Box）
- 文本内容和属性提取
- Accessibility Tree 信息

**感知方法对比**:

| 方法 | 优势 | 劣势 |
|------|------|------|
| 纯截图 | 所见即所得，适用性广 | 精度有限，难定位具体元素 |
| 纯 DOM | 结构化信息丰富，定位精确 | 信息量大，动态内容难处理 |
| 截图 + DOM 混合 | 互补优势，精度和理解力兼顾 | 实现复杂度高，Token 消耗大 |
| Set-of-Mark | 在截图上标注元素编号，兼顾视觉和结构 | 标注生成有开销 |

### 2. 决策层 (Decision)

**任务规划**:
- 将高层任务分解为子任务序列
- 基于当前状态选择下一步操作
- 支持多步推理和长期规划

**常用 Prompt 策略**:
- ReAct (Reasoning + Acting): 交替推理和执行
- Chain-of-Thought: 逐步推理
- 反思机制: 操作后自我检查

### 3. 执行层 (Action)

**基本操作集**:
- `click(element)`: 点击元素
- `type(element, text)`: 输入文本
- `scroll(direction)`: 页面滚动
- `navigate(url)`: 页面导航
- `select(element, value)`: 下拉选择
- `hover(element)`: 悬停
- `wait(condition)`: 等待条件
- `screenshot()`: 截图
- `extract(selector)`: 数据提取
- `go_back()`: 返回上一页
- `switch_tab(index)`: 切换标签页

---

## 主流 GUI Agent 框架对比

| 特性 | browser-use | Midscene | WebArena | SeeAct | Mind2Web |
|------|-------------|----------|----------|--------|----------|
| 目标场景 | 通用浏览器任务 | UI 测试自动化 | Agent 评测 | 网页操作 | 真实网站任务 |
| 感知方式 | DOM + 截图 | 截图 + AI 语义 | DOM + 截图 | 截图 + SoM | HTML + 截图 |
| LLM 支持 | 多种 | 多种 | 多种 | GPT-4V | GPT-4 |
| 开源 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 底层引擎 | Playwright | Playwright/Puppeteer | Playwright | Playwright | - |
| 多标签支持 | ✅ | ❌ | ✅ | ❌ | ❌ |
| 自纠错 | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## 评测体系

### 常用评测基准

| 基准 | 说明 |
|------|------|
| **WebArena** | 真实网页环境评测，包含 812 个任务 |
| **Mind2Web** | 2000+ 真实网站任务评测 |
| **VisualWebArena** | 侧重视觉理解的网页 Agent 评测 |
| **WebVoyager** | 端到端网页导航评测 |
| **OSWorld** | 跨操作系统的桌面 Agent 评测 |
| **GAIA** | 通用 AI 助手评测基准 |

### 关键评测指标

- **任务成功率 (Task Success Rate)**: 成功完成任务的比例
- **步骤效率 (Step Efficiency)**: 完成任务所需的步骤数
- **操作准确率 (Action Accuracy)**: 每步操作的正确率
- **元素定位准确率 (Element Grounding)**: 正确定位目标元素的比例
- **错误恢复率 (Error Recovery)**: 从错误状态恢复的能力
- **端到端延迟 (E2E Latency)**: 任务完成的总耗时

### 常见问题与优化策略

| 问题 | 原因 | 优化策略 |
|------|------|----------|
| 元素定位失败 | DOM 过于复杂 | DOM 简化 + Set-of-Mark |
| 操作幻觉 | LLM 产生不存在的操作 | 限制 Action Space + 验证 |
| 长任务失败 | 上下文丢失 | 记忆机制 + 任务分解 |
| 动态页面处理差 | 页面状态变化 | 智能等待 + 状态检测 |
| Token 消耗大 | DOM 信息量过大 | DOM 裁剪 + 关键信息提取 |
| 速度慢 | 每步需 LLM 推理 | 操作缓存 + 轻量模型分级 |

---

## 与当前项目的关系

本项目 (ai-chat-chrome) 是一个 Chrome 扩展，提供 AI 聊天功能。BrowserAgent 的学习可以帮助我们：

1. **扩展 AI 能力**: 从对话式 AI 扩展到操作式 AI，让 AI 不仅能回答问题，还能帮助用户操作网页
2. **Chrome 扩展集成**: 基于 Chrome 扩展的架构，可以将 BrowserAgent 集成为高级功能
3. **页面理解**: 利用 content script 的页面访问能力，增强 AI 对当前页面的理解
4. **自动化操作**: 基于用户指令自动完成网页操作任务

---

## 延伸阅读

### 论文
- [WebAgent: A Large Language Model Based Web Agent](https://arxiv.org/abs/2307.12856)
- [Mind2Web: Towards a Generalist Agent for the Web](https://arxiv.org/abs/2306.06070)
- [SeeAct: GPT-4V(ision) is a Generalist Web Agent](https://arxiv.org/abs/2401.01614)
- [WebArena: A Realistic Web Environment for Building Autonomous Agents](https://arxiv.org/abs/2307.13854)
- [VisualWebArena: Evaluating Multimodal Agents on Realistic Visual Web Tasks](https://arxiv.org/abs/2401.13649)
- [MobileAgent: Enhancing Mobile Control via Human-Machine Interaction and SOP Integration](https://arxiv.org/abs/2401.16158)
- [Set-of-Mark Prompting Unleashes Extraordinary Visual Grounding in GPT-4V](https://arxiv.org/abs/2310.11441)

### 开源项目
- [browser-use](https://github.com/browser-use/browser-use) - LLM 浏览器自动化
- [Midscene](https://github.com/web-infra-dev/midscene) - AI UI 自动化
- [MobileAgent](https://github.com/X-PLUG/MobileAgent) - 移动端多模态 Agent
- [WebArena](https://github.com/web-arena-x/webarena) - Agent 评测环境
- [Playwright](https://playwright.dev/python/) - 浏览器自动化引擎
- [AgentGPT](https://github.com/reworkd/AgentGPT) - AI Agent 平台
- [LaVague](https://github.com/lavague-ai/LaVague) - 基于 LLM 的 Web Agent
