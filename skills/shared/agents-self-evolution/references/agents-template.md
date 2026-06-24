# `AGENTS.md` 模板

将此文件作为项目级起点。保持精简，把详细业务与技术上下文放到 `docs/ai-context`。

```md
# 项目指导

## 项目目标

- 用 2-5 条简要说明项目做什么。
- 标明主要用户、外部系统和业务目标。
- 深度上下文入口：`docs/ai-context/README.md`

## 工作原则

- 优先使用仓库内可验证事实，不凭印象下结论。
- 保留用户已有修改和现有项目约定。
- 改动保持小而可追踪。
- 每次改动运行最小必要验证。
- 若业务行为不明确，先记录候选说明，不要直接发明规则。

## 业务上下文

权威业务上下文位于：

- `docs/ai-context/business-domain.md`
- `docs/ai-context/glossary.md`
- `docs/ai-context/workflows.md`
- `docs/ai-context/data-model.md`
- `docs/ai-context/integration-map.md`
- `docs/ai-context/decisions.md`
- `docs/ai-context/open-questions.md`

当 Codex 发现稳定业务逻辑时，若该事实由用户说明、代码、测试、数据库 schema 或现有文档直接支持，可以更新这些文件。

Codex 不得静默把推断出的业务行为升级为权威规则。存在不确定性时，应写入 `open-questions.md`，并附带来源和置信度。

## 自更新策略

当用户重复纠正、发现稳定项目约定、或缺少本地上下文导致重复摩擦时，Codex 可以自动更新低风险指导信息。

当 Serena 可用于当前项目时，Codex 应优先使用 Serena memories 记录动态 learned rules、corrections、observations 和 open questions。

仓库内文档应用于共享、可审阅、应版本化保存的稳定上下文，例如业务规则、术语表、工作流、结构图和架构决策。

Codex 可以直接更新：

- 格式和回复偏好
- 已验证的项目命令
- 客观项目结构图
- 反复出现的低风险用户偏好
- 由代码、测试、schema、文档或用户明确说明确认的业务术语
- 完成非一次性的编码、调试、评审或重构任务后，新发现的稳定上下文

以下内容必须先写候选说明或先询问：

- 安全、隐私、凭据、认证、权限、破坏性命令策略
- 发布、迁移、计费、合规、数据保留、生产行为
- 没有明确证据支持的用户可见业务规则
- 与现有指导看起来冲突的新信息

每次自更新都应带上足够的回滚信息：

- trigger: 触发原因
- rule: 新增或变更的规则
- scope: global / project / directory / module / task type
- source: 用户说明、文件路径、命令结果、测试、schema 或文档
- confidence: high / medium / low
- rollback: 如何移除或回滚

每次完成非一次性的编码、调试、评审或重构任务后，Codex 应做一次简短自检：

- 是否发现了值得长期沉淀的稳定上下文
- 是否存在会让后续代理重复犯错的事实或约束

若答案为是，应以最小变更更新 `docs/ai-context/*`、`AGENTS.md` 或 Serena memories，而不是等用户再次提醒。

## 默认收尾动作

每次完成非一次性的编码、调试、评审或重构任务后，默认执行以下收尾动作：

1. 判断本次任务是否产生了可复用、可长期保存的上下文。
2. 若产生了，则归类为：
   - 项目结构 / 模块边界 / 代码归属
   - 业务规则 / 领域理解
   - 术语 / 别名 / 易混淆概念
   - 业务或技术工作流
   - 已验证命令 / 构建测试约束
   - 用户偏好 / 重复纠错
3. 按最小合适位置沉淀：
   - `AGENTS.md`：简短规则、索引、默认行为
   - `docs/ai-context/business-domain.md`：已验证业务逻辑
   - `docs/ai-context/project-structure.md`：结构与边界
   - `docs/ai-context/glossary.md`：术语
   - `docs/ai-context/workflows.md`：流程
   - Serena memories：动态规则、观察、候选说明、演进日志
4. 证据不足时，写入 `open-questions.md` 或相关 Serena memory，不要写成确定事实。
5. 最终回复只汇报真正有意义的沉淀，不输出噪音。

推荐的 Serena memory 名称：

- `ai/corrections`
- `ai/observations`
- `ai/learned-rules`
- `ai/evolution-log`
- `ai/open-questions`

## 文档语言

- 业务说明、架构解释、术语、流程、决策和开放问题优先使用中文。
- 路径、类名、接口名、方法名、配置键、命令、环境变量保留英文原文。
- 推荐写法：中文说明 + 反引号中的代码锚点。

## 编码

- 文档、脚本、模板和 AI 维护的上下文统一使用 UTF-8。
- Python 读写文本必须显式传入 `encoding="utf-8"`。
- Windows 环境优先设置 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`、PowerShell UTF-8 profile 和 `chcp 65001`。
- Git 优先设置 `i18n.commitEncoding=utf-8`、`i18n.logOutputEncoding=utf-8`、`core.quotepath=false`。
- 不要默认依赖 GBK/CP936；只有遗留文件或外部系统明确要求时才使用，并在命令或文档中标明例外。

## 项目结构

当前结构图入口：

- `docs/ai-context/project-structure.md`

Codex 应通过真实文件检查后更新该结构图，而不是凭记忆补写。

## 验证

- 在这里记录已验证的 build / test / lint 命令。
- 如本地无法运行，说明缺少的前置条件。

## 工具与 MCP 边界

- 仅在能显著提升准确性或结构化上下文获取时使用 MCP。
- 未经明确授权，不要访问生产数据库或使用敏感凭据。
- 优先只读检查，再执行写操作。
```
