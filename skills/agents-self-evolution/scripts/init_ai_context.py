#!/usr/bin/env python3
"""Create a Chinese-first AI-context skeleton for project documentation."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path


TODAY = date.today().isoformat()


FILES = {
    "docs/ai-context/README.md": """# AI 上下文索引

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

- 动态、临时、会演化的信息优先写入 Serena memories。
- 共享、稳定、可审阅的事实写入本目录。
- 每条业务规则都要写来源和置信度。
- 不确定行为放到 `open-questions.md`。
- 本目录文档统一使用 UTF-8，不要默认依赖 GBK/CP936。
""",
    "docs/ai-context/project-structure.md": """# 项目结构

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
""",
    "docs/ai-context/business-domain.md": f"""# 业务域

## 业务规则

### 规则：初始占位

- rule: unknown
- scope: unknown
- source: 初始化 AI 上下文骨架
- confidence: low
- updated: {TODAY}
- owner: unknown
- exceptions: none
- open questions: 请用已验证的业务规则替换本占位内容

## 不变量

- unknown

## 禁止假设

- 没有证据时，不要把推断出的业务行为写成权威规则。
""",
    "docs/ai-context/glossary.md": f"""# 术语表

| 术语 | 含义 | 别名 | 来源 | 置信度 | 更新时间 |
|---|---|---|---|---|---|
| unknown | unknown | unknown | 初始化 AI 上下文骨架 | low | {TODAY} |

## 易混淆术语

- unknown
""",
    "docs/ai-context/workflows.md": f"""# 工作流

## 工作流：初始占位

- actors: unknown
- trigger: unknown
- happy path: unknown
- alternative paths: unknown
- failure handling: unknown
- state transitions: unknown
- source: 初始化 AI 上下文骨架
- confidence: low
- updated: {TODAY}
- open questions: 请用已验证的工作流替换本占位内容
""",
    "docs/ai-context/data-model.md": """# 数据模型

## 实体

| 实体 | 含义 | 关键字段 | 来源 | 置信度 |
|---|---|---|---|---|
| unknown | unknown | unknown | 初始化 AI 上下文骨架 | low |

## 关系

| From | To | 关系 | 约束 | 来源 |
|---|---|---|---|---|
| unknown | unknown | unknown | unknown | unknown |

## 数据规则

- unknown
""",
    "docs/ai-context/integration-map.md": """# 集成关系图

| 系统 | 方向 | 协议 | 用途 | Owner | 来源 | 置信度 |
|---|---|---|---|---|---|---|
| unknown | unknown | unknown | unknown | unknown | 初始化 AI 上下文骨架 | low |

## 队列与事件

| 事件/队列 | 生产者 | 消费者 | 载荷 | 保证 | 来源 |
|---|---|---|---|---|---|
| unknown | unknown | unknown | unknown | unknown | unknown |

## 定时任务

| 任务 | 调度 | 用途 | 副作用 | 来源 |
|---|---|---|---|---|
| unknown | unknown | unknown | unknown | unknown |
""",
    "docs/ai-context/decisions.md": """# 决策记录

## 决策：初始占位

- status: proposed
- date: YYYY-MM-DD
- context: unknown
- decision: unknown
- consequences: unknown
- source: 初始化 AI 上下文骨架
- supersedes: none
""",
    "docs/ai-context/open-questions.md": f"""# 开放问题

## 问题：初始业务上下文

- question: 当前最应该先沉淀的业务规则是什么？
- why it matters: AI 需要已验证的上下文，才能避免编造业务行为。
- current assumption: none
- risk if wrong: 后续代理可能对产品或业务领域做出错误假设。
- source: 初始化 AI 上下文骨架
- confidence: low
- created: {TODAY}
- resolved: no
""",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Create AI-context skeleton files.")
    parser.add_argument("project_root", help="Project root where files should be created")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files instead of preserving them",
    )
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    root.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []
    skipped: list[Path] = []
    for relative, content in FILES.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not args.overwrite:
            skipped.append(path)
            continue
        path.write_text(content, encoding="utf-8", newline="\n")
        created.append(path)

    print(f"Project root: {root}")
    print(f"Created: {len(created)}")
    for path in created:
        print(f"  + {path}")
    print(f"Skipped: {len(skipped)}")
    for path in skipped:
        print(f"  = {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
