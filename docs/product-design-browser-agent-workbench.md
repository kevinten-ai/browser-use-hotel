# 产品设计：AgentLens — 浏览器智能体透镜

> 让 AI 操作浏览器的每一步都看得见、比得出、学得会

---

## 一、为什么做这个产品

### 1.1 生态空白分析

调研 browser-use 生态后，发现一个显著空白：

| 已有工具 | 能做什么 | 缺什么 |
|----------|---------|--------|
| Laminar | 追踪 Agent 步骤 + 录屏 | 无法看 LLM 推理细节，无策略对比 |
| LangSmith/Langfuse | Token/延迟/成本指标 | **看不到 Agent 做决策时看到的画面** |
| browser-use GIF | 生成执行动画 | 事后查看，无法交互，无中间数据 |
| PageBolt | 视觉回放 | 通用工具，非教学导向 |
| browser-use Web-UI | Gradio 界面执行任务 | 无可观测性，无学习引导 |

**核心缺口**：没有一个工具能像 ai-rag-pipeline 那样，将 Agent 的每一步（感知/推理/执行/验证）都拆解为可观测、可对比、可调参的透明流水线。

### 1.2 为什么是"透镜"而不是"工具箱"

ai-rag-pipeline 成功的原因不是它能做 RAG，而是它让你**看懂 RAG 是怎么工作的**。同理，我们不是要做一个更好的 browser-use 前端，而是要做一个让人**看懂 BrowserAgent 是怎么工作的**透镜。

```
普通工具：输入任务 → 黑盒执行 → 返回结果
AgentLens：输入任务 → 每步透视（感知/推理/执行/验证）→ 策略对比 → 理解原理
```

---

## 二、产品定义

### 2.1 一句话描述

**AgentLens** 是一个透明白盒的浏览器智能体平台，基于 browser-use 引擎，将 Agent 的"感知-推理-执行-验证"循环完全可视化，同时提供真实的自动化任务能力。

### 2.2 与 ai-rag-pipeline 的对应关系

| ai-rag-pipeline | AgentLens |
|-----------------|-----------|
| 页面：文档摄入工坊（/ingest） | 页面：任务执行观测台（/execute） |
| 页面：RAG 问答（/query） | 页面：智能助手（/assistant） |
| 页面：策略实验室（/lab） | 页面：策略对比实验室（/lab） |
| 页面：知识库管理（/knowledge） | 页面：任务历史与回放（/history） |
| 组件：PipelineFlow（流水线） | 组件：AgentLoop（Agent 循环） |
| 组件：TracePanel（追踪面板） | 组件：StepTrace（步骤追踪） |
| 组件：VectorPreview（向量预览） | 组件：DOMPreview（DOM 预览） |
| 组件：EmbeddingSpace3D（3D空间） | 组件：PageAnnotation（页面标注） |
| 组件：ChunkComparison（分块对比） | 组件：PerceptionCompare（感知对比） |
| 数据结构：RAGTrace | 数据结构：AgentTrace |

### 2.3 核心设计原则

1. **每步都有 Trace** — 感知产出截图+DOM，推理产出思考链，执行产出动作+结果，验证产出前后对比
2. **实时而非事后** — WebSocket 推送，看 Agent "活"着工作
3. **可对比可实验** — 同一任务不同策略，雷达图展示差异
4. **有实用价值** — 不只是 Demo，能真正完成数据提取、表单填写、网站测试等任务

---

## 三、Glass Box 流水线设计

### 3.1 RAG Pipeline vs Agent Loop

RAG 是**线性流水线**（A → B → C → D → E → F），Agent 是**循环**（每步重复感知→推理→执行→验证，直到任务完成）。这是两种不同的可视化挑战。

```
RAG Pipeline（线性）:
  查询理解 → 向量化 → 检索 → 重排序 → Prompt构造 → LLM生成
  ────────────────────────────────────────────────────────→

Agent Loop（循环）:
  ┌─→ 感知 → 推理 → 执行 → 验证 ─┐
  │                               │
  │   (页面状态发生变化)           │
  │                               │
  └───────────── 继续 ────────────┘
                 ↓ (任务完成)
               结束
```

**设计策略**：将循环展开为**步骤时间线**，每步是一个完整的"迷你流水线"。

### 3.2 单步 Trace 结构（核心数据模型）

```typescript
// ===== 对标 ai-rag-pipeline 的 RAGTrace =====

interface AgentTrace {
  id: string;
  task: string;                    // 自然语言任务
  status: 'running' | 'completed' | 'failed';
  totalDurationMs: number;
  totalSteps: number;
  totalTokens: number;
  totalCost: number;

  // Agent 配置快照
  config: {
    llmModel: string;              // 使用的 LLM
    perceptionMode: 'dom' | 'vision' | 'hybrid';  // 感知模式
    maxSteps: number;
    useVision: boolean;
  };

  // 展开的步骤列表
  steps: AgentStepTrace[];
}

interface AgentStepTrace {
  stepNumber: number;
  durationMs: number;

  // ── 阶段1: 感知 (对标 RAG 的 "查询理解+向量化") ──
  perception: {
    durationMs: number;

    // 截图通道
    screenshot: {
      image: string;              // base64 截图
      width: number;
      height: number;
    };

    // DOM 通道
    dom: {
      totalNodes: number;         // 原始 DOM 节点数
      filteredNodes: number;      // 过滤后节点数
      interactiveElements: number; // 可交互元素数
      domTree: string;            // 精简后的 DOM 文本表示
      elements: Array<{
        index: number;            // 元素索引 [1], [2]...
        tag: string;              // 标签名
        type: string;             // 元素类型 (button, input, link...)
        text: string;             // 可见文本
        rect: { x: number; y: number; w: number; h: number };
        isVisible: boolean;
        isInteractive: boolean;
      }>;
    };

    // 标注截图 (在截图上标注元素编号)
    annotatedScreenshot: string;   // base64

    // 感知统计
    stats: {
      domExtractionMs: number;
      screenshotMs: number;
      annotationMs: number;
      viewportCoverage: number;   // 视口覆盖率
    };
  };

  // ── 阶段2: 推理 (对标 RAG 的 "Prompt构造+LLM生成") ──
  reasoning: {
    durationMs: number;
    tokensUsed: { prompt: number; completion: number; total: number };

    // LLM 输入 (完整 Prompt)
    prompt: {
      systemMessage: string;       // 系统提示词
      stateDescription: string;    // 页面状态描述
      taskProgress: string;        // 任务进度
      memoryContent: string[];     // 记忆内容
      fullPromptTokens: number;
    };

    // LLM 输出 (推理过程)
    output: {
      thinking: string;           // 内部思考过程 (CoT)
      currentStateAnalysis: string; // "我看到了什么"
      goalProgress: string;        // "离目标还有多远"
      nextAction: string;          // "我决定做什么"
      confidence: number;          // 置信度 0-1
      alternatives: string[];      // 备选方案
    };

    estimatedCost: number;
  };

  // ── 阶段3: 执行 (对标 RAG 的 "检索") ──
  execution: {
    durationMs: number;
    action: {
      type: string;                // click, type, scroll, navigate...
      params: Record<string, any>; // 动作参数
      targetElement?: {
        index: number;
        text: string;
        coordinates: [number, number];
      };
    };
    success: boolean;
    error?: string;
    playwrightCommand: string;     // 实际执行的 Playwright 命令
  };

  // ── 阶段4: 验证 (对标 RAG 的 "重排序") ──
  verification: {
    durationMs: number;
    beforeScreenshot: string;      // 执行前截图
    afterScreenshot: string;       // 执行后截图
    stateChanged: boolean;         // 页面是否发生变化
    verdict: 'success' | 'failure' | 'no_effect' | 'unexpected';
    diff: string;                  // 状态差异描述
    shouldRetry: boolean;
  };

  // ── 元数据 ──
  meta: {
    cumulativeTokens: number;      // 累计 Token
    cumulativeCost: number;        // 累计费用
    memoryUpdates: string[];       // 本步记忆更新
    url: string;                   // 当前页面 URL
    pageTitle: string;             // 页面标题
  };
}
```

### 3.3 可视化组件对照表

| ai-rag-pipeline 组件 | AgentLens 对应组件 | 展示内容 |
|-------------------|--------------------|----------|
| `PipelineFlow` | `AgentTimeline` | 步骤时间线，每步显示 4 个阶段图标+状态 |
| `TracePanel` (6步) | `StepDetailPanel` (4阶段) | 单步的 4 阶段详细数据 |
| `TraceTimeline` (耗时条) | `StepDurationBar` | 每步各阶段的耗时条形图 |
| `CostEstimator` | `CostTracker` | 实时累计 Token/费用 |
| `VectorPreview` | `DOMTreeViewer` | 可折叠的 DOM 树浏览器 |
| `EmbeddingSpace3D` | `PageAnnotationOverlay` | 截图上标注可交互元素的叠加层 |
| `SimilarityHeatmap` | `ScreenshotDiffView` | 执行前后截图滑动对比 |
| `ChunkComparison` | `PerceptionModeCompare` | DOM/视觉/混合感知结果对比 |
| `RerankComparison` | `ActionAlternatives` | LLM 选择的动作 vs 备选动作 |
| `StreamingAnswer` | `ThinkingStream` | LLM 推理过程流式展示 |
| `PromptViewer` | `PromptInspector` | 发给 LLM 的完整 Prompt |
| `SourceAttribution` | `MemoryPanel` | Agent 当前记忆内容 |

---

## 四、四个页面设计

### 页面 1：任务执行观测台（/execute）— 核心页面

**对标 ai-rag-pipeline 的 /query 页面**

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🎯 任务输入栏                                                       │
│ ┌─────────────────────────────────────────┐  ┌──────┐ ┌──────────┐ │
│ │ "去豆瓣电影搜索评分最高的科幻电影..."    │  │ ▶ 执行│ │ ⏯ 单步模式│ │
│ └─────────────────────────────────────────┘  └──────┘ └──────────┘ │
│                                                                     │
│ ⚙️ LLM: GPT-4o ▼  |  感知: 混合模式 ▼  |  最大步数: 20            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─── 左侧：浏览器实时画面 ──┐  ┌─── 右侧：Agent 视角 ──────────┐ │
│  │                           │  │                                │ │
│  │   🖥️ 浏览器截图            │  │  🤖 标注截图                   │ │
│  │   (真实页面)               │  │  (元素编号叠加)                │ │
│  │                           │  │  [1] 搜索框                   │ │
│  │                           │  │  [2] 搜索按钮                 │ │
│  │                           │  │  [3] 导航-电影                │ │
│  │                           │  │  ...                          │ │
│  └───────────────────────────┘  └────────────────────────────────┘ │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  📊 步骤时间线 (AgentTimeline)                                      │
│  ┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌────┐                           │
│  │ S1 │→│ S2 │→│ S3 │→│ S4 │→│ S5 │→ ...                        │
│  │ ✅ │  │ ✅ │  │ ✅ │  │🔄 │  │ ○  │                           │
│  │2.1s│  │3.4s│  │1.8s│  │... │  │    │                           │
│  └────┘  └────┘  └────┘  └────┘  └────┘                           │
│  点击任意步骤展开 ↓                                                 │
├─────────────────────────────────────────────────────────────────────┤
│  🔍 Step 3 详细追踪 (StepDetailPanel)                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │ 👁 感知   │ │ 🧠 推理   │ │ ⚡ 执行   │ │ ✓ 验证   │              │
│  │  0.3s    │ │  2.1s    │ │  0.5s    │ │  0.5s    │              │
│  │ 18个元素  │ │ 1,247tok │ │ click[3] │ │ ✅ 成功   │              │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │
│                                                                     │
│  🧠 推理详情（展开态）:                                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 💭 思考: "当前在豆瓣首页，看到顶部有'电影'导航链接[3]，     │   │
│  │    我需要先进入电影频道，然后寻找评分排行功能。"              │   │
│  │                                                             │   │
│  │ 🎯 进度: 任务第 1/4 步 — 导航到电影频道                     │   │
│  │ 🔧 决策: click(element=[3]) — 点击"电影"导航                │   │
│  │ 📊 置信度: 0.95  |  备选: click[1]搜索框直接搜索 (0.7)      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  📈 实时统计:  Token: 4,832 | 费用: $0.038 | 步骤: 3/20           │
└─────────────────────────────────────────────────────────────────────┘
```

### 页面 2：策略对比实验室（/lab）

**对标 ai-rag-pipeline 的 /lab 页面**

同一任务，不同配置，并排对比。

**对比维度 A：感知策略**
```
┌────────────────────┬────────────────────┬────────────────────┐
│   纯 DOM 模式       │   纯视觉模式       │   混合模式（默认）  │
├────────────────────┼────────────────────┼────────────────────┤
│  DOM 树文本表示     │  截图 + LLM 描述    │  DOM + 截图        │
│  18 个可交互元素    │  "我看到一个搜索页  │  18 元素 + 截图    │
│                    │   面，顶部有..."    │                    │
├────────────────────┼────────────────────┼────────────────────┤
│  Token: 2,100      │  Token: 1,800      │  Token: 3,200      │
│  准确率: 85%        │  准确率: 72%        │  准确率: 92%       │
│  耗时: 1.2s        │  耗时: 2.5s        │  耗时: 2.8s        │
└────────────────────┴────────────────────┴────────────────────┘
```

**对比维度 B：LLM 模型**
```
┌────────────────────┬────────────────────┬────────────────────┐
│   GPT-4o           │   Claude Sonnet    │   DeepSeek-V3      │
├────────────────────┼────────────────────┼────────────────────┤
│  成功率: 87%        │  成功率: 82%       │  成功率: 75%       │
│  平均步数: 6.2      │  平均步数: 5.8     │  平均步数: 7.1     │
│  平均耗时: 45s      │  平均耗时: 52s     │  平均耗时: 38s     │
│  Token费: $0.12     │  Token费: $0.09    │  Token费: $0.02    │
└────────────────────┴────────────────────┴────────────────────┘

雷达图: 成功率 / 效率 / 成本 / 推理质量 / 错误恢复
```

**对比维度 C：Prompt 策略**

| 策略 | 描述 | 适用场景 |
|------|------|----------|
| ReAct | 每步 Observe→Think→Act | 通用场景 |
| Plan-first | 先规划完整计划再执行 | 复杂多步任务 |
| Minimal | 最小化 Prompt | 成本敏感 |
| Reflexion | 执行后反思 + 修正 | 容错要求高 |

### 页面 3：任务历史与回放（/history）

**对标 ai-rag-pipeline 的 /knowledge 页面**

- 历史任务列表（状态、步数、成功率、费用）
- 点击任务进入 **回放模式**（逐步播放，可快进/暂停）
- **失败分析报告**：自动识别失败原因 + 优化建议
- 统计仪表盘：成功率趋势、常见失败类型、费用分布

### 页面 4：首页仪表盘（/）

**对标 ai-rag-pipeline 的 / 页面**

```
┌─────────────────────────────────────────────────────┐
│  📊 统计概览                                         │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐               │
│  │ 42   │ │ 78%  │ │ $2.3 │ │ 6.5  │               │
│  │总任务 │ │成功率│ │总费用 │ │平均步数│               │
│  └──────┘ └──────┘ └──────┘ └──────┘               │
│                                                      │
│  🚀 快速开始                                         │
│  ┌──────────────┐ ┌──────────────┐                  │
│  │ 📝 新建任务   │ │ 🔬 策略实验   │                  │
│  │ 输入任务描述  │ │ 对比不同策略  │                  │
│  └──────────────┘ └──────────────┘                  │
│  ┌──────────────┐ ┌──────────────┐                  │
│  │ 📖 引导教程   │ │ 📂 回放历史   │                  │
│  │ 从零学Agent  │ │ 查看执行记录  │                  │
│  └──────────────┘ └──────────────┘                  │
│                                                      │
│  ⏱ 最近任务                                         │
│  · "搜索豆瓣电影TOP250"   ✅ 成功  5步  $0.04       │
│  · "填写简历投递表"       ❌ 失败  12步 $0.15       │
│  · "提取商品价格对比"     ✅ 成功  8步  $0.07       │
└─────────────────────────────────────────────────────┘
```

---

## 五、三个杀手级使用场景

### 场景 1：智能数据提取（最实用）

```
任务: "去 GitHub Trending 页面，提取今天 Python 类 Top 10 仓库的名称、Stars、描述"

Agent 执行过程（可观测）:
  Step 1: navigate("github.com/trending")
          → 感知: 页面有语言筛选器[1], 时间筛选器[2], 仓库列表[3-12]
          → 推理: "需要先筛选 Python 语言"

  Step 2: click([1] 语言筛选器)
          → 验证: 弹出了语言下拉菜单 ✅

  Step 3: click("Python" 选项)
          → 验证: 页面刷新，显示 Python 仓库 ✅

  Step 4: extract(仓库列表 → 结构化数据)
          → 输出:
          | # | 仓库名 | Stars | 描述 |
          |---|--------|-------|------|
          | 1 | xxx    | 1.2k  | ...  |
          | 2 | yyy    | 890   | ...  |
          ...

观测价值:
  · 看到 Agent 如何理解 "筛选Python" 这个子任务
  · 看到 DOM 提取如何将列表转为结构化数据
  · 看到 extract 操作如何调用 LLM 做数据结构化
```

### 场景 2：表单自动填写（最直观）

```
任务: "在示例表单页面填写：姓名张三，邮箱test@example.com，选择城市北京，提交"

Agent 执行过程:
  Step 1: 感知 → 识别4个表单字段 [1]姓名 [2]邮箱 [3]城市下拉 [4]提交按钮
  Step 2: type([1], "张三") → 验证：输入框显示"张三" ✅
  Step 3: type([2], "test@example.com") → 验证 ✅
  Step 4: click([3]) → select("北京") → 验证 ✅
  Step 5: click([4] 提交) → 验证：显示"提交成功" ✅

观测价值:
  · 表单场景步骤清晰，适合入门学习
  · 每步都有明确的"执行前→执行后"对比
  · 可以故意制造错误（如邮箱格式不对）观察 Agent 如何处理
```

### 场景 3：网站功能测试（最有深度）

```
任务: "测试登录功能：用错误密码登录，验证是否显示错误提示；再用正确密码登录，验证是否跳转到首页"

Agent 执行过程:
  Step 1-3: 导航到登录页 → 输入用户名 → 输入错误密码
  Step 4: click(登录按钮)
          → 验证: 页面显示"密码错误"提示 ✅ (视觉断言)
  Step 5-7: 清空密码框 → 输入正确密码 → 点击登录
  Step 8: 验证: 页面跳转到首页，显示用户名 ✅

观测价值:
  · 展示 Agent 的"视觉断言"能力（不靠选择器，靠"看"页面）
  · 展示多步骤任务的规划和记忆
  · 展示错误场景下的 Agent 行为
```

---

## 六、技术架构

### 6.1 整体架构

```
┌────────────────────────────────────────────────────────────┐
│                  Frontend (Next.js + TypeScript)            │
│                                                            │
│  /               /execute          /lab         /history   │
│  Dashboard       Live Observatory  Strategy Lab  Replay    │
│                                                            │
│  UI: shadcn/ui + Tailwind CSS (对齐 ai-rag-pipeline)       │
│  可视化: Recharts (图表) + Canvas (页面标注)                 │
│  通信: WebSocket (实时推送) + REST (历史查询)               │
└──────────────────────┬─────────────────────────────────────┘
                       │
              WebSocket │ REST API
                       │
┌──────────────────────▼─────────────────────────────────────┐
│                  Backend (FastAPI + Python)                  │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           AgentOrchestrator (编排器)                  │   │
│  │                                                     │   │
│  │  ┌───────────┐                                      │   │
│  │  │ browser-  │  Agent 引擎                           │   │
│  │  │ use       │  (感知-推理-执行-验证循环)             │   │
│  │  └─────┬─────┘                                      │   │
│  │        │                                            │   │
│  │  ┌─────▼─────┐  ┌──────────┐  ┌───────────────┐    │   │
│  │  │TraceLogger│  │LLM Router│  │BrowserManager │    │   │
│  │  │追踪记录器 │  │模型路由器│  │浏览器管理器   │    │   │
│  │  └───────────┘  └──────────┘  └───────────────┘    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                            │
│  数据层: SQLite (Trace 持久化) + 文件系统 (截图存储)        │
└────────────────────────────────────────────────────────────┘
                                          │
                                ┌─────────▼─────────┐
                                │  Playwright        │
                                │  (Chromium 实例)    │
                                └───────────────────┘
```

### 6.2 关键技术决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 前端框架 | Next.js + TypeScript | 与 ai-rag-pipeline 一致，便于学员迁移 |
| UI 组件 | shadcn/ui + Tailwind | 与 ai-rag-pipeline 一致 |
| 后端框架 | FastAPI (Python) | browser-use 是 Python，原生集成 |
| 实时通信 | WebSocket | Agent 循环需要实时推送 |
| Agent 引擎 | browser-use | 培训指定框架 |
| 数据存储 | SQLite | 轻量，零部署依赖 |
| 截图存储 | 本地文件 | 简单可靠 |

### 6.3 browser-use 集成方式

```python
from browser_use import Agent, Browser
from browser_use.agent.views import AgentOutput
import asyncio

class TracedAgent:
    """可追踪的 Agent 封装 — 核心集成点"""

    def __init__(self, task: str, llm, websocket):
        self.ws = websocket
        self.trace = AgentTrace(task=task)

        self.agent = Agent(
            task=task,
            llm=llm,
            browser=Browser(),
            # browser-use 支持的回调/钩子
            save_conversation_path="./traces/",   # 保存对话历史
            generate_gif=True,                     # 生成 GIF
        )

    async def run_with_trace(self):
        """执行任务并实时推送 Trace 数据"""

        # 方案: 包装 agent.step() 方法，在每步前后注入追踪逻辑
        original_step = self.agent.step

        async def traced_step(*args, **kwargs):
            step_trace = AgentStepTrace(stepNumber=self.trace.step_count + 1)

            # 1. 感知阶段 — 截取当前状态
            step_trace.perception = await self._capture_perception()
            await self.ws.send_json({"type": "perception", "data": step_trace.perception})

            # 2. 推理+执行 — 调用原始 step
            result = await original_step(*args, **kwargs)

            # 3. 提取推理数据
            step_trace.reasoning = self._extract_reasoning(result)
            await self.ws.send_json({"type": "reasoning", "data": step_trace.reasoning})

            # 4. 提取执行数据
            step_trace.execution = self._extract_execution(result)
            await self.ws.send_json({"type": "execution", "data": step_trace.execution})

            # 5. 验证阶段 — 截取新状态并对比
            step_trace.verification = await self._capture_verification()
            await self.ws.send_json({"type": "verification", "data": step_trace.verification})

            self.trace.steps.append(step_trace)
            return result

        self.agent.step = traced_step
        result = await self.agent.run()
        return self.trace
```

---

## 七、MVP 范围（4 周）

### Week 1: 基础框架

- [ ] FastAPI 后端骨架 + WebSocket 端点
- [ ] Next.js 前端骨架（4 个页面路由）
- [ ] browser-use Agent 基本集成
- [ ] AgentTrace 数据模型定义

### Week 2: 核心观测台

- [ ] 左右分屏：浏览器截图 + 标注截图
- [ ] 步骤时间线组件 (AgentTimeline)
- [ ] 单步详情面板 (StepDetailPanel)：感知/推理/执行/验证 4 个 Tab
- [ ] LLM 推理过程流式展示 (ThinkingStream)
- [ ] 实时 Token/费用计数器

### Week 3: 回放与分析

- [ ] Trace 数据持久化 (SQLite)
- [ ] 截图存储与管理
- [ ] 任务历史列表
- [ ] 回放模式：逐步播放 + 快进/暂停
- [ ] 执行前后截图对比 (ScreenshotDiffView)

### Week 4: 策略实验室

- [ ] 感知模式切换（DOM / 视觉 / 混合）
- [ ] LLM 模型切换
- [ ] 并排对比布局
- [ ] 统计对比图表

---

## 八、学习路径设计

### Level 1：Hello Agent（30分钟）

```
引导任务："让 Agent 打开百度搜索'今天天气'"

学习目标:
  ✅ 理解 Agent 的基本循环：感知→推理→执行
  ✅ 看到 DOM 提取的结果（"Agent 看到了什么"）
  ✅ 看到 LLM 的推理过程（"Agent 怎么想的"）
  ✅ 理解为什么 Agent 选择这个动作而不是其他
```

### Level 2：感知之眼（1小时）

```
实验任务: "同一个任务，分别用 DOM 模式、视觉模式、混合模式执行"

学习目标:
  ✅ DOM 提取如何将页面转化为结构化数据
  ✅ 多模态 LLM 如何"看"截图
  ✅ 不同感知策略对成功率、Token、速度的影响
  ✅ 理解 browser-use 的 Set-of-Mark 标注机制
```

### Level 3：推理之脑（1小时）

```
实验任务: "对比不同 LLM 执行同一复杂任务的推理过程"

学习目标:
  ✅ 不同 LLM 的推理风格差异
  ✅ Prompt 策略（ReAct vs Plan-first）的影响
  ✅ Token 消耗与推理质量的权衡
  ✅ 置信度与备选方案的含义
```

### Level 4：纠错之力（1小时）

```
挑战任务: "故意给一个会失败的任务，观察 Agent 如何检测和恢复错误"

学习目标:
  ✅ 验证阶段如何检测执行失败
  ✅ Agent 的重试和回退机制
  ✅ 记忆系统如何帮助避免重复错误
  ✅ 常见失败模式和优化策略
```

---

## 九、名称与品牌

**推荐名称**：**AgentLens** （智能体透镜）

寓意：
- **Lens**（透镜）= 让不可见的变得可见
- 像 Chrome DevTools 是 Web 开发的透镜一样，AgentLens 是 BrowserAgent 的透镜
- 简短好记，技术感强

---

## 十、总结

| 维度 | AgentLens 方案 |
|------|---------------|
| 核心差异 | 市面唯一的 BrowserAgent 透明白盒平台 |
| 实用价值 | 数据提取、表单填写、网站测试 |
| 学习价值 | 4 级学习路径，从 Hello Agent 到纠错优化 |
| 技术可行性 | 基于 browser-use 成熟框架，4 周可出 MVP |
| 设计对齐 | 组件/页面/数据结构完全对标 ai-rag-pipeline |
| 生态定位 | 填补 browser-use 生态的"可观测性+教育"空白 |
