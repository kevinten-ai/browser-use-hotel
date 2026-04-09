# MobileAgent 项目深度调研

## 一、项目概览

MobileAgent 是阿里巴巴 X-PLUG 团队开发的 GUI 智能体家族，经历了从 v1 到 v3.5 的完整演进，同时衍生出 PC-Agent（桌面端）、Mobile-Agent-E（自进化版本）、GUI-Critic-R1（错误诊断组件）等子项目。

---

## 二、版本演进

### Mobile-Agent v1（ICLR 2024 Workshop）
**单智能体 + 纯视觉感知**

核心组件：
- GPT-4V 作为推理引擎
- OCR 模型用于文字检测与定位
- Grounding DINO + CLIP 用于图标识别与匹配

关键特性：
- 纯视觉方案，不依赖 XML 或系统元数据
- ReAct 式提示结构（Observation → Thought → Action）
- 8 种操作：Open App、Click Text、Click Icon、Type、Page Up/Down、Back、Exit、Stop

### Mobile-Agent v2（NeurIPS 2024）
**三智能体协作 + 记忆单元**

| 智能体 | 使用模型 | 核心职能 |
|--------|---------|---------|
| 规划智能体 | GPT-4（纯文本） | 将操作历史压缩为纯文本任务进度摘要 |
| 决策智能体 | GPT-4V（多模态） | 根据当前状态生成具体操作 |
| 反思智能体 | GPT-4V（多模态） | 对比操作前后截图，分类为错误/无效/正确操作 |

**记忆单元**：存储跨页面/跨应用的关键信息（如验证码、地址等），对多应用场景至关重要。

### Mobile-Agent v3
**四智能体 + 自训练基座模型**

| 角色 | 职能 |
|------|------|
| Manager | 子目标分解，外部知识检索 |
| Worker | GUI 操作执行 |
| Reflector | 预期 vs 实际结果对比诊断 |
| Notetaker | 持久化记忆维护 |

核心创新：用自训练的 **GUI-Owl** 基座模型替代外部工具组合。

### Mobile-Agent v3.5（最新 SOTA）
- 基于 **Qwen3-VL** 构建的 **GUI-Owl-1.5**
- 支持移动端、桌面端、浏览器、车载系统
- 三阶段训练：预训练 → 监督微调 → MRPO 强化学习
- 2B 模型在 OSWorld 上超越 10 倍参数量的 UI-TARS-72B

---

## 三、关键差异总结

| 维度 | v1 | v2 | v3/v3.5 |
|------|----|----|---------|
| 架构 | 单智能体 | 三智能体 | 四智能体 + 端到端模型 |
| 感知 | OCR + 图标检测 | 增强 OCR + Qwen-VL | GUI-Owl 统一感知 |
| 记忆 | 无 | 记忆单元 | Notetaker 智能体 |
| 跨平台 | 仅移动端 | 仅移动端 | 手机/桌面/浏览器/车载 |

---

## 四、评估结果

### v3.5 SOTA 成绩

| 基准 | 得分 |
|------|------|
| OSWorld-Verified | **56.5%** (超越 Claude-4、Gemini-2.5-Pro) |
| AndroidWorld | **71.6%** |
| WebArena | 46.7% |
| WebVoyager | 78.1% |
| ScreenSpot-V2 | 95.3% (32B) |

---

## 五、与桌面浏览器智能体的对比

| 维度 | MobileAgent | 桌面浏览器智能体 |
|------|-------------|----------------|
| 感知方式 | 纯视觉（截图 + OCR → 端到端 VLM） | DOM 解析 + 视觉 |
| 操作空间 | 触控（Tap、Swipe、Type） | 鼠标键盘（Click、Type、Scroll） |
| 跨应用 | 原生多 App 切换 | 浏览器标签页切换 |
| 结构化信息 | 无 DOM，依赖视觉 | 可获取 HTML DOM |

v3.5 模糊了移动端/桌面端/浏览器智能体的边界，代表了从"单平台专用"向"多平台通用"演进的趋势。
