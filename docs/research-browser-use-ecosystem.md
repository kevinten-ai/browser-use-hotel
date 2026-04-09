# Browser-Use 生态系统调研

## 一、官方生态

| 项目 | 说明 |
|------|------|
| [Browser-Use Cloud](https://browser-use.com) | 商业化云平台，BU 2.0 模型比前沿模型便宜 15x、快 6x |
| [Web-UI](https://github.com/browser-use/web-ui) | Gradio Web 界面 |
| [Workflow-Use](https://github.com/browser-use/workflow-use) | RPA 2.0，录制一次→AI 回放，失败自动回退到 Agent |
| [Agent-SDK](https://github.com/browser-use/agent-sdk) | 极简 Agent 框架 |
| [Template Library](https://github.com/browser-use/template-library) | 官方模板库（shopping/job-application/slack 等） |
| [MCP Server](https://docs.browser-use.com/customize/integrations/mcp-server) | 可集成 Claude Code/Desktop |

## 二、社区热门项目

| 项目 | 说明 |
|------|------|
| [Rebrowse](https://github.com/zk1tty/rebrowse-app) | "Loom for workflow"，录屏→100个可执行工作流 |
| [SDET-GENIE](https://github.com/WaiGenie/SDET-GENIE) | 用户故事→自动化测试代码 |
| [SpiderCreator](https://github.com/carlosplanchon/spidercreator) | LLM 自动生成爬虫 |
| [nanobrowser](https://github.com/nanobrowser/nanobrowser) | 浏览器内多 Agent 系统 |
| [OpenManus](https://github.com/mannaandpoem/OpenManus) | 受 Manus 启发的开源多 Agent |

## 三、可观测性工具现状

| 工具 | 能力 | 缺口 |
|------|------|------|
| Laminar | Agent 步骤追踪 + 录屏 | 无 LLM 推理细节，无策略对比 |
| LangSmith/Langfuse | Token/延迟/成本 | **看不到 Agent 做决策时看到的画面** |
| PageBolt | 视觉回放 + 决策流程 | 通用工具，非教学导向 |
| AgentPrism | OpenTelemetry trace 可视化 | React 组件，需自行集成 |
| browser-use 内置 | GIF + HAR + 命令行日志 | 事后查看，无法交互 |

**核心空白：没有工具能将 Agent 的视觉感知 + LLM 推理链 + 执行过程 统一在一个交互式面板中**

## 四、社区最大痛点

1. **成功率不稳定**（30%-89%），多步任务需人工干预
2. **反 Bot 检测弱**，不原生支持 CAPTCHA/2FA
3. **生产部署困难**，Docker 问题频发
4. **LLM 成本高**，每步都需推理
5. **调试困难**，缺乏可视化调试工具

## 五、竞品格局

| 竞品 | 定位 | 优势 |
|------|------|------|
| Browserbase/Stagehand | 浏览器基础设施 | $40M 融资，5000万+会话 |
| Skyvern | 计算机视觉+LLM | 表单填写最强（85.85%） |
| Manus AI | 多能力 Agent | 编码+多模态+自主规划 |
| Airtop | 无代码平台 | 内置 CAPTCHA/2FA 处理 |

## 六、生态空白（机会）

1. **可视化调试平台** — 将感知/推理/执行统一可视化 ← **我们的方向**
2. 混合策略（AI 探索 + 确定性回放）降本
3. 反检测/安全中间件
4. 多 Agent 协作编排
5. 垂直领域专业化
6. 移动端浏览器 Agent
