# Insight Synapse
## MVP Implementation Plan Specification
### MVP実装計画書 v0.1

---

# 1. 目的

本ドキュメントは、Insight Synapseの最初の実装段階（MVP）における開発範囲、実装順序、完成条件を定義する。

目的：

> 複雑なAIプラットフォームを作る前に、思考・判断・評価・改善の循環が成立する最小システムを構築する。

---

# 2. MVPの定義

Insight Synapse MVPとは、

「高度なAIエージェント」

ではない。

最低限、

```text
Goal

↓

State理解

↓

Decision

↓

Execution

↓

Evaluation

↓

Memory
```

が循環するシステムである。

---

# 3. MVP対象範囲

実装するもの：

```text
✓ Orchestrator

✓ State管理

✓ Skill実行

✓ Workflow管理

✓ Evaluation

✓ Thought Trace Memory

✓ Claude Code統合
```

---

# 4. MVPで作らないもの

初期では不要。

```text
× 複雑なUI

× Vector Database

× 自律Agent大量生成

× 高度なKnowledge Graph

× 完全自動自己改変
```

---

# 5. MVPアーキテクチャ

```text
User

↓

Claude Code

↓

Insight Synapse Core

↓

Orchestrator

↓

Workflow

↓

Skill

↓

Execution

↓

Evaluation

↓

Memory
```

---

# 6. Phase 1
## Foundation

## 目的

基本構造を作る。

---

## 作成ファイル

```text
core/

├── state/

│   └── state.yaml


├── orchestrator/

│   └── orchestrator.md


└── decision/

    └── decision_log.md
```

---

## 完成条件

AIが現在状態を保持できる。

---

# 7. Phase 2
## Memory System

## 目的

思考履歴保存。

---

## 作成：

```text
memory/

├── traces/

├── decisions/

└── patterns/
```

---

## 保存形式

Markdown。

---

例：

```markdown
# Decision Trace

Goal:

AI制作基盤


Decision:

Evaluation優先


Reason:

改善能力が重要なため
```

---

## 完成条件

AIの判断理由が後から確認できる。

---

# 8. Phase 3
## Orchestrator

## 目的

判断制御。

---

実装内容：

- Goal解析
- Phase判断
- Cost判断
- Skill選択

---

判断例：

```text
Unknown 高

↓

Research Skill

↓

Explore Workflow
```

---

完成条件：

AIが次の行動理由を説明できる。

---

# 9. Phase 4
## Evaluation Engine

## 目的

改善ループ構築。

---

初期評価：

```text
Quality

Logic

Creativity

Value

Risk
```

---

出力：

```markdown
Score:

0.8

Weakness:

構造不足

Improvement:

追加分析
```

---

完成条件：

評価結果がMemoryへ反映される。

---

# 10. Phase 5
## Skill System

## 目的

能力を分離。

---

初期Skill：

```text
skills/

├── question

├── analyze

├── structure

├── create

├── evaluate

└── reflect
```

---

完成条件：

Skillを組み合わせて処理できる。

---

# 11. Phase 6
## Workflow Engine

## 目的

処理の流れ管理。

---

初期Workflow：

```text
creation

research

problem-solving

learning
```

---

例：

Creation：

```text
Research

↓

Structure

↓

Create

↓

Evaluate
```

---

完成条件：

目的別に処理経路を変更できる。

---

# 12. Phase 7
## Claude Code Integration

## 目的

実開発環境化。

---

配置：

```text
.claude/

├── CLAUDE.md

└── skills/
```

---

CLAUDE.md役割：

- 開発ルール
- 思考ルール
- 保存ルール

---

完成条件：

Claude CodeからInsight Synapseを利用できる。

---

# 13. 最初のデモシナリオ

検証テーマ：

「Insight Synapse自身を改善する」

---

流れ：

```text
User:

リポジトリ改善案を作る


↓

Orchestrator:

分析不足を検出


↓

Research Skill


↓

Structure Skill


↓

Create Proposal


↓

Evaluation


↓

Memory保存
```

---

# 14. MVP評価基準

成功条件：

## Criterion 1

判断理由が残る。

---

## Criterion 2

改善履歴が残る。

---

## Criterion 3

同じ問題で以前より良い判断ができる。

---

## Criterion 4

人間が途中介入できる。

---

# 15. 開発優先順位

優先度：

```text
1. Memory

2. Orchestrator

3. Evaluation

4. Skill

5. Workflow

6. UI
```

---

# 16. 推奨技術スタック

## Runtime

Claude Code

---

## Data

Markdown

YAML

Git

---

## Backend（必要になったら）

Python

Node.js

---

## UI（後段）

Simple Web App

---

# 17. 開発期間目安

## Proof of Concept

数日

範囲：

- Memory
- Decision
- Simple Evaluation

---

## MVP

数週間

範囲：

- Skill
- Workflow
- Claude統合

---

## 実用版

数ヶ月

範囲：

- UI
- Agent
- External Tools

---

# 18. 最初のリポジトリ作成手順

```bash
mkdir insight-synapse

cd insight-synapse

git init

mkdir core memory skills workflows evaluation
```

---

# 19. 最初にClaude Codeへ渡す指示

```markdown
あなたはInsight Synapse開発AIです。

目的：

思考・制作・評価・改善を循環するAI基盤を作る。

原則：

- 判断理由を保存する
- Layer責務を守る
- 変更理由を記録する
- 小さく実装する
```

---

# 20. 最終定義

Insight Synapse MVPとは、

> AIを自律化することではなく、AIが考え、判断し、評価され、経験として蓄積される最小循環を実証するための実験基盤である。

最初に作るべきものは、

「賢いAI」

ではなく、

**成長できるAIの構造**

である。