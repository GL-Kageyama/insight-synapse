# Insight Synapse
## Claude Code Setup Guide
### Claude Code実装開始手順書 v0.1

---

# 1. 目的

本ドキュメントは、Claude Codeを開発AIとして利用し、Insight Synapseリポジトリを構築するための初期設定を定義する。

目的：

> Claude Codeが単なるコード生成ツールではなく、Insight Synapseの設計思想を理解した開発パートナーとして動作する環境を作る。

---

# 2. 開発思想

Claude Codeへの基本方針：

```text
コードを書く前に構造を理解する。

変更する前に理由を確認する。

実装より設計整合性を優先する。
```

---

# 3. 初期ディレクトリ作成

```bash
mkdir insight-synapse

cd insight-synapse

git init
```

---

作成：

```text
insight-synapse/

├── .claude/

├── core/

├── workflows/

├── skills/

├── primitives/

├── agents/

├── evaluation/

├── memory/

├── governance/

├── interface/

└── docs/
```

---

# 4. Claude Code設定

## .claude/CLAUDE.md

Claude Codeの基本人格・開発ルールを定義する。

---

配置：

```text
.claude/

└── CLAUDE.md
```

---

内容：

```markdown
# Insight Synapse Development Rules


## Role

あなたはInsight Synapse開発AIです。


## Mission

思考・制作・評価・改善を循環するAI基盤を構築する。


## Principles

1. 設計思想を維持する

2. Layer責務を混ぜない

3. 判断理由を残す

4. 小さく実装する

5. 変更履歴を管理する


## Architecture

Core:
判断


Workflow:
流れ


Skill:
能力


Primitive:
思考操作


Memory:
経験保存


Evaluation:
改善
```

---

# 5. Claude Codeの最初の確認

最初に実行：

```text
リポジトリ構造を分析してください。

Insight Synapseの設計思想を理解してください。

不足している部分を報告してください。
```

---

# 6. 開発フロー

基本サイクル：

```text
理解

↓

設計

↓

実装

↓

評価

↓

Memory保存

↓

改善
```

---

# 7. Issue管理

変更はIssue単位で管理する。

例：

```markdown
# Issue

## Goal

Memory Layerを作成する


## Reason

思考履歴保存が必要


## Success Criteria

Decision Traceが保存される
```

---

# 8. Commitルール

1変更 = 1理由

---

例：

```bash
git commit -m "
Add thought trace memory

Reason:
Enable decision history tracking
"
```

---

# 9. 開発優先順序

Claude Codeには以下順序で作らせる。

---

## Step 1

Memory Foundation

作成：

```text
memory/

├── traces

├── decisions

└── patterns
```

---

## Step 2

State管理

作成：

```text
core/state
```

---

## Step 3

Orchestrator

作成：

```text
core/orchestrator
```

---

## Step 4

Evaluation

作成：

```text
evaluation/
```

---

## Step 5

Skill Framework

作成：

```text
skills/
```

---

## Step 6

Workflow

作成：

```text
workflows/
```

---

# 10. Claude Codeへの実装指示テンプレート

```markdown
# Task

〇〇機能を実装してください。


# Context

Insight Synapseでは、
〇〇は△△の役割を持つ。


# Requirements

- 責務を限定する
- Memoryへ記録する
- Markdown中心で管理する


# Output

変更内容

理由

今後の拡張案

を報告してください。
```

---

# 11. AI開発時の禁止事項

## 禁止1

巨大なコードを一度に作る。

---

## 禁止2

Layerを跨いだ直接依存。

---

悪い例：

```text
Skill

↓

Memory直接操作
```

---

良い例：

```text
Skill

↓

Orchestrator

↓

Memory
```

---

## 禁止3

判断理由なしの変更。

---

# 12. Development Memory

開発そのものも記録する。

保存：

```text
memory/

└── development/

    ├── decisions/

    ├── failures/

    └── lessons/
```

---

# 13. テスト方針

最初は機能テストより思想テストを重視する。

確認：

```text
この変更は、

Insight Synapseの思想に合っているか？
```

---

# 14. MVP最初の実験

テーマ：

「AI自身にリポジトリ改善案を作らせる」

---

流れ：

```text
User Goal

↓

Orchestrator

↓

Research

↓

Structure

↓

Proposal

↓

Evaluation

↓

Memory
```

---

# 15. 完成状態

初期成功：

```text
Claude Code

↓

Insight Synapse

↓

自分自身を改善する提案

↓

履歴保存
```

---

# 16. 将来拡張

## Agent Marketplace

Skill/Agent共有。

---

## Visual Interface

思考状態可視化。

---

## Autonomous Improvement

自己改善ループ。

---

## External Tool Integration

外部サービス連携。

---

# 17. 最終定義

Claude Code環境におけるInsight Synapseとは、

> AIにコードを書かせる環境ではなく、AIが設計思想を理解し、判断履歴を残しながら、継続的に改善する開発基盤である。

最初の目標は、

**AIに作らせることではなく、AIと共に設計を進化させること**

である。