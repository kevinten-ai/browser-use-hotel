# Browser-Use 框架深度调研

## 一、项目概览与最新版本

**Browser-Use** 是一个开源的 Python AI Agent 框架，使大语言模型（LLM）能够自主控制真实浏览器，通过自然语言指令完成网页自动化任务。项目采用 MIT 许可证，截至 2026 年 3 月：

- **最新版本**：v0.12.2（2026 年 3 月 12 日发布）
- **GitHub Stars**：81.1k
- **Forks**：9.6k
- **依赖项目数**：2,400+
- **主要语言**：Python（98.3%）
- **Python 要求**：>= 3.11

### 近期重要更新

| 版本 | 日期 | 关键更新 |
|------|------|----------|
| v0.12.2 | 2026-03-12 | 修复 CDP 窗口创建、增强导航后 DOM 检测重试逻辑、严格数据接地规则减少幻觉、改进滚动指令 |
| v0.12.1 | 2026-03-03 | 恢复 cookie/localStorage 通过 storage_state、修复代理认证冲突、改进 MCP 截图处理 |
| v0.12.0 | 2026-02-26 | 锁定所有依赖版本、增强 CSV 生成能力 |
| v0.11.13 | 2026-02-25 | **自动 CAPTCHA 求解器**（看门狗机制）、WebSocket 重连、save_as_pdf 动作 |
| v0.11.11 | 2026-02-20 | 浏览器关闭时 Agent 自动停止、自定义 headers 支持、结构化输出附带文件 |
| v0.11.9 | 2026-02-06 | **基础 Agent 规划能力**、动作循环检测、HAR 录制、消息压缩 |

**BU 2.0 模型**（2026 年 1 月 27 日）：Browser-Use 专有优化模型，准确率从 74.7% 提升至 83.3%（+12%），平均任务时长约 62 秒，与 Claude Opus 4.5 准确率持平但快 40%。

---

## 二、详细架构解析

### 核心组件交互

Browser-Use 采用 **感知-行动循环（Perceive-Act Loop）** 架构：

```
┌─────────────────────────────────────────────────┐
│                    Agent（主协调器）               │
│  ┌───────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ MessageMgr│  │  Memory  │  │  Controller  │  │
│  │ 会话管理   │  │ 过程记忆  │  │  动作注册表   │  │
│  └───────────┘  └──────────┘  └──────────────┘  │
└────────┬────────────────────────────┬────────────┘
         │                            │
    ┌────▼────┐                 ┌─────▼─────┐
    │   LLM   │                 │  Browser  │
    │ 决策引擎  │                 │ 浏览器控制 │
    └─────────┘                 └─────┬─────┘
                                      │
                              ┌───────▼───────┐
                              │ BrowserContext │
                              │   会话隔离     │
                              └───────┬───────┘
                                      │
                              ┌───────▼───────┐
                              │  DOMService   │
                              │  DOM 提取处理  │
                              └───────────────┘
```

### 1. Agent（智能代理）
核心协调器，负责：向 LLM 发送当前浏览器状态（DOM 快照 + 截图 + 历史上下文），解析 LLM 返回的动作指令，通过 Controller 执行动作，循环直至任务完成或达到最大步数。

### 2. Browser（浏览器）
基于 **Playwright** 构建，通过 WebSocket 通信：支持 Chromium / Firefox / WebKit，支持有头/无头模式，支持远程调试端口（默认 9222）。

### 3. Controller / Registry（控制器/注册表）
管理 Agent 可调用的所有动作，支持通过 `@tools.action()` 装饰器注册自定义动作。

### 4. DOM 提取机制（DOMService）
核心创新 — `buildDomTree.js` 注入页面分析 DOM，过滤非必要元素，识别可交互元素，分配数字索引 ID，生成精简层次化 DOM 表示。

---

## 三、关键配置选项

### Agent 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `task` | str | 必填 | 自然语言任务描述 |
| `llm` | BaseChatModel | 必填 | LangChain 兼容的 LLM |
| `use_vision` | str/bool | `"auto"` | 视觉模式 |
| `max_actions_per_step` | int | `4` | 每步最大动作数 |
| `max_failures` | int | `3` | 最大连续失败次数 |
| `max_steps` | int | `100` | 最大执行步数 |
| `flash_mode` | bool | `False` | 快速模式 |
| `sensitive_data` | dict | None | 敏感数据（按域名映射） |
| `generate_gif` | bool/str | `False` | 生成操作过程 GIF |

---

## 四、高级功能

### 自定义动作
```python
from browser_use import Tools, ActionResult
tools = Tools()

@tools.action(description='询问人类输入', allowed_domains=['example.com'])
def ask_human(question: str) -> ActionResult:
    answer = input(f'{question} > ')
    return ActionResult(extracted_content=answer, include_in_memory=True)
```

### 敏感数据处理
LLM 通过占位符引用敏感数据，永远不直接看到真实值。

### 多代理并行执行
支持主 Agent 将高级任务拆分为子任务，分发给多个 Worker Agent（实验性功能）。

### CAPTCHA 自动求解（v0.11.13+）
通过看门狗机制自动检测和处理 CAPTCHA。

### 动作循环检测（v0.11.9+）
检测并打破 Agent 陷入重复动作循环的情况。

---

## 五、性能与局限

### 性能
- BU 2.0 准确率 83.3%，平均任务时长 ~62 秒
- `flash_mode=True` 跳过评估和思考，提升速度
- 消息压缩机制优化长对话的 token 使用

### 已知限制
1. 执行速度较慢，单次操作可能需数十秒
2. 超时错误频繁（>30s）
3. DOM 检测在复杂页面存在问题
4. Agent 可能产生幻觉数据
5. 多代理并行为实验性功能

---

## 六、社区生态

- 81.1k Stars，AI Agent 开源项目领先
- 深度集成 LangChain 生态
- 支持所有主流 LLM 提供商
- Browser Use Cloud 提供托管平台
