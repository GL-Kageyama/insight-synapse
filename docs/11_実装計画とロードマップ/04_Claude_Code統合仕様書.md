# Insight Synapse
## Claude Code Integration Specification
### Claude Code統合仕様書 v0.1

---

# 1. 目的

本ドキュメントは、Insight SynapseをClaude Code環境上で実行するための構成、設定、利用方法を定義する。

目的：

> Claude Codeを利用して、思考・制作・評価・記憶の循環を持つAI開発環境を構築する。

---

# 2. 基本思想

Claude Code：

```text
実行環境
```

Insight Synapse：

```text
思考システム
```

として分離する。

構造：

```text
Human

↓

Claude Code

↓

Insight Synapse Framework

↓

Memory / Skill / Workflow

↓

Output
```

---

# 3. Claude Code内の役割

Claude Codeが担当する。

## 実行

- ファイル操作
- コード生成
- Skill呼び出し
- Memory更新
- Git操作

---

## 担当しないもの

- 独自判断基準
- 長期記憶
- 評価基準

これらはInsight Synapse側で管理する。

---

# 4. ディレクトリ構成

Claude Code用：

```text
insight-synapse/

├── .claude/

│
│   ├── CLAUDE.md
│   │
│   └── skills/
│
│       ├── synapse-think/
│       │
│       ├── synapse-create/
│       │
│       └── synapse-evaluate/


├── core/

├── skills/

├── primitives/

├── memory/

├── workflows/

└── evaluation/
```

> **正版**：最終リポジトリ構成は `10_環境とリポジトリ/02_最終リポジトリ構成仕様書.md`。本節はClaude Code連携に必要なMVP簡略図であり、本書を最終形とする。

---

# 5. CLAUDE.md設計

CLAUDE.mdはClaude Codeへの基本人格ではなく、

「開発ルール」

として利用する。

---

例：

```markdown
# Insight Synapse Development Rules

## Role

You are an AI development assistant operating inside Insight Synapse.


## Principles

- Separate thinking from execution
- Record important decisions
- Evaluate before finalizing
- Prefer reusable structures


## Workflow

Always:

1. Check Current State
2. Identify Next Action
3. Execute Skill
4. Save Trace
5. Evaluate Result
```

---

# 6. Claude Skill統合

Claude CodeのSkill機能を利用する。

配置：

```text
.claude/skills/

├── synapse-think/

│   └── SKILL.md


├── synapse-create/

│   └── SKILL.md


└── synapse-evaluate/

    └── SKILL.md
```

---

# 7. synapse-think Skill

目的：

思考開始。

処理：

```text
Input

↓

Current State確認

↓

Unknown抽出

↓

Orchestrator判断

↓

Next Action生成
```

---

SKILL.md例：

```markdown
# Synapse Think

Purpose:

Start reasoning process.

Steps:

1. Read current state
2. Analyze unknowns
3. Select workflow
4. Update trace
```

---

# 8. synapse-create Skill

目的：

制作実行。

処理：

```text
Workflow確認

↓

Creation Skill選択

↓

Primitive実行

↓

Artifact生成

↓

保存
```

---

# 9. synapse-evaluate Skill

目的：

評価実行。

処理：

```text
Artifact取得

↓

Criteria確認

↓

Evaluation実行

↓

Report生成

↓

Memory更新
```

---

# 10. コマンド設計

MVPでは自然言語でも可能。

将来的にはコマンド化する。

---

## Think

```text
/synapse think
```

処理：

- 状態確認
- 判断
- 次Action提示

---

## Create

```text
/synapse create
```

処理：

- 制作Workflow開始

---

## Evaluate

```text
/synapse evaluate
```

処理：

- 評価実行
- 改善案生成

---

## Status

```text
/synapse status
```

表示：

```text
Current Phase

Confidence

Unknown

Next Action
```

---

# 11. 実行フロー

例：

ユーザー：

```text
新しいサービス案を作りたい
```

---

Claude Code：

↓

State生成

```yaml
goal:
service design

phase:
unknown
```

↓

Orchestrator：

```text
Action:
Explore
```

↓

Skill：

```text
Explore Skill
```

↓

Memory：

```text
Trace保存
```

↓

Evaluation：

```text
改善点確認
```

---

# 12. Memory更新方式

Claude Code実行後：

必ず確認する。

保存対象：

```text
memory/traces/

YYYYMMDD_topic.md
```

---

例：

```markdown
# Thought Trace

Decision:

Explore first


Reason:

Unknownが多いため


Result:

良い方向性を発見
```

---

# 13. Git連携

Gitを思考履歴として利用する。

推奨：

1 Action = 1 Commit

例：

```text
Add creation workflow

Reason:
Enable reusable production process
```

---

# 14. Agent化について

MVPでは大量Agentを作らない。

優先：

```text
Orchestrator

↓

Skill

↓

Primitive
```

---

必要になった場合のみ：

```text
Evaluator Agent

Research Agent

Creator Agent
```

を追加する。

---

# 15. MVP完成状態

以下が動けば成功。

```text
User Goal

↓

Claude Code

↓

Insight Synapse

↓

Decision

↓

Creation

↓

Evaluation

↓

Memory

↓

Improved Decision
```

---

# 16. 将来拡張

## Phase 2

- MCP連携
- 外部ツール接続
- Vector Memory


## Phase 3

- Multi Agent Evaluation
- Autonomous Workflow Generation


## Phase 4

- 複数AI協調環境

---

# 17. 最終定義

Insight Synapse Claude Code Integrationとは、

> Claude Codeを実行基盤として利用し、思考構造・判断基準・制作能力・評価能力を統合したAI開発環境を構築するための統合設計である。

Claude Codeは手足であり、Insight SynapseはAIの「考え方を管理する脳構造」である。