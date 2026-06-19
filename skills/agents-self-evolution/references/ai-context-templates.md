# AI 上下文模板

这些模板用于沉淀业务逻辑和项目结构，同时避免把 `AGENTS.md` 写成百科全书。

动态、临时、会持续演化的信息优先放 Serena memories。以下 repo 文件用于共享、稳定、可审阅的上下文。

## `docs/ai-context/README.md`

```md
# AI 上下文索引

本目录用于存放 AI 与团队共享的项目知识。

- `project-structure.md`：仓库结构、入口点、模块边界
- `business-domain.md`：核心业务概念与业务规则
- `glossary.md`：术语、别名、禁止混淆的词
- `workflows.md`：业务或技术工作流
- `data-model.md`：实体、关系、关键约束
- `integration-map.md`：外部系统、API、队列、定时任务
- `decisions.md`：稳定的架构或实现决策
- `open-questions.md`：尚未确认的问题和假设

规则：

- 每条业务规则都要写来源和置信度。
- 优先写具体事实，不写空泛总结。
- 不确定或推断出的行为放到 `open-questions.md`。
- 规则有变化时更新时间。
- 本目录文档统一使用 UTF-8，不要默认依赖 GBK/CP936。
```

## `project-structure.md`

```md
# 项目结构

## 入口点

| 区域 | 路径 | 作用 | 验证方式 |
|---|---|---|---|
| unknown | unknown | unknown | unknown |

## 模块边界

| 模块 | 路径 | 负责内容 | 可依赖 | 不应依赖 |
|---|---|---|---|---|
| unknown | unknown | unknown | unknown | unknown |

## 注册点

| 机制 | 路径 | 说明 |
|---|---|---|
| DI | unknown | unknown |
| Routes | unknown | unknown |
| Jobs | unknown | unknown |
| Events | unknown | unknown |

## 测试

| 测试类型 | 路径 | 命令 | 说明 |
|---|---|---|---|
| unknown | unknown | unknown | unknown |

## 生成代码或脆弱区域

- unknown
```

## `business-domain.md`

```md
# 业务域

## 业务规则

### 规则：<简短名称>

- rule: <具体行为>
- scope: <模块/功能/角色/租户/地区/环境>
- source: <用户说明、文件路径、测试、schema、API 文档或观察结果>
- confidence: <high|medium|low>
- updated: YYYY-MM-DD
- owner: <团队/人员/unknown>
- exceptions: <none|list>
- open questions: <none|list>

## 不变量

- <必须始终成立的事实>

## 禁止假设

- <AI 没有证据时不应擅自假设的内容>
```

## `glossary.md`

```md
# 术语表

| 术语 | 含义 | 别名 | 来源 | 置信度 | 更新时间 |
|---|---|---|---|---|---|
| unknown | unknown | unknown | unknown | low | YYYY-MM-DD |

## 易混淆术语

- `<term>`：可能含义，以及何时必须先确认
```

## `workflows.md`

```md
# 工作流

## 工作流：<名称>

- actors: <参与者/系统>
- trigger: <触发条件>
- happy path:
- alternative paths:
- failure handling:
- state transitions:
- source:
- confidence:
- updated:
- open questions:
```

## `data-model.md`

```md
# 数据模型

## 实体

| 实体 | 含义 | 关键字段 | 来源 | 置信度 |
|---|---|---|---|---|
| unknown | unknown | unknown | unknown | low |

## 关系

| From | To | 关系 | 约束 | 来源 |
|---|---|---|---|---|
| unknown | unknown | unknown | unknown | unknown |

## 数据规则

- <校验、生命周期、保留、唯一性、归属规则>
```

## `integration-map.md`

```md
# 集成关系图

| 系统 | 方向 | 协议 | 用途 | Owner | 来源 | 置信度 |
|---|---|---|---|---|---|---|
| unknown | unknown | unknown | unknown | unknown | unknown | low |

## 队列与事件

| 事件/队列 | 生产者 | 消费者 | 载荷 | 保证 | 来源 |
|---|---|---|---|---|---|
| unknown | unknown | unknown | unknown | unknown | unknown |

## 定时任务

| 任务 | 调度 | 用途 | 副作用 | 来源 |
|---|---|---|---|---|
| unknown | unknown | unknown | unknown | unknown |
```

## `decisions.md`

```md
# 决策记录

## 决策：<简短名称>

- status: proposed | accepted | deprecated | superseded
- date: YYYY-MM-DD
- context:
- decision:
- consequences:
- source:
- supersedes:
```

## `open-questions.md`

```md
# 开放问题

## 问题：<简短名称>

- question:
- why it matters:
- current assumption:
- risk if wrong:
- source:
- confidence: low
- created: YYYY-MM-DD
- resolved:
```

推荐的 Serena memory 名称：

- `ai/corrections`
- `ai/observations`
- `ai/learned-rules`
- `ai/evolution-log`
- `ai/open-questions`
