# Insight Synapse
## Claude Code Execution Plan
### Claude Code実装実行計画書 v0.1

---

# 1. 目的

本ドキュメントは、Claude Codeを使用してInsight Synapseを実装するための開発手順を定義する。

目的：

> 設計思想を失わず、AI開発エージェントと協調して段階的にシステムを構築する。

---

# 2. Claude Codeの役割

Claude Codeは単なるコード生成ツールではない。

役割：

```text id="v4m8k2"
設計理解

↓

実装

↓

テスト

↓

改善提案

↓

設計Memory更新
```

---

# 3. 開発開始時に読むファイル

Claude Code起動時：

必ず確認する。

```text id="q8n3m5"
README.md

↓

CLAUDE.md

↓

docs/

├── Architecture

├── Technical Specification

├── Data Model

├── API Design

├── Test Strategy

└── MVP Criteria
```

---

# 4. 開発原則

## Principle 1

設計書を優先する。

```text id="m2x7p9"
コードを書く

↓

設計と矛盾確認

↓

必要なら設計変更
```

---

## Principle 2

小さく実装する。

```text id="r5n8k3"
Small Feature

↓

Test

↓

Memory Update
```

---

## Principle 3

判断理由を残す。

すべての重要変更：

```markdown id="u6p2m4"
変更内容:

理由:

影響:

判断:
```

を保存する。

---

# 5. 実装フェーズ

---

# Phase 0
## Repository Setup

## 目的

開発基盤作成。

---

実行：

```text id="w8m3q5"
Repository作成

Folder作成

Config作成

Test環境作成
```

---

完成条件：

```text id="x3n7k9"
コード追加可能な状態
```

---

# Phase 1
## Memory Core

最初に作る。

理由：

Insight Synapseの中心だから。

---

実装：

```text id="c7m2p8"
Memory Manager

↓

Trace Storage

↓

Decision Storage

↓

Pattern Storage
```

---

保存形式：

Markdown + YAML

---

テスト：

```text id="j4n8v2"
保存できる

取得できる

履歴が残る
```

---

# Phase 2
## Orchestrator

## 実装

役割：

```text
状態を見る

↓

次行動を決める

↓

Workflowを選択
```

---

重要：

判断理由を必ず出力。

---

# Phase 3
## Evaluation Engine

## 実装

評価：

```text
Quality

Logic

Creativity

Value

Risk
```

---

出力：

- Score
- Weakness
- Improvement

---

# Phase 4
## Primitive Layer

## 実装

基本思考操作。

```text
decompose
compare
abstract
reframe
generate
synthesize
evaluate
reflect
```

---

目的：

Skillを構成する基礎。

---

# Phase 5
## Skill Layer

## 実装

初期Skill：

```text
question
analyze
structure
create
evaluate
reflect
```

---

ルール：

SkillはPrimitiveを利用する。

---

# Phase 6
## Workflow Engine

## 実装

形式：

```yaml
workflow:
  steps:
    - analyze
    - create
    - evaluate
```

---

確認：

順番制御。

エラー処理。

---

# Phase 7
## API Layer

実装：

```text id="h8n4p2"
POST /goal

POST /decision

POST /evaluate

POST /memory/save
```

---

# Phase 8
## First POC完成

実験：

```text id="b6m9q3"
アイデア入力

↓

判断

↓

評価

↓

Memory保存
```

---

# 6. Claude Codeへの指示テンプレート

機能追加時：

```markdown id="d5x8m2"
## Task

実装内容:


## Context

関連設計:


## Requirements

必要条件:


## Test

確認方法:


## Memory

判断記録:
```

---

# 7. Claude Code禁止事項

## 禁止1

勝手な巨大設計変更。

---

## 禁止2

不要なFramework追加。

---

## 禁止3

Memoryを無視した実装。

---

## 禁止4

判断理由を残さない変更。

---

# 8. コードレビュー基準

確認：

```text id="e7m2q5"
責務分離されているか？

Memory化可能か？

Testがあるか？

将来拡張可能か？
```

---

# 9. 開発サイクル

基本ループ：

```text id="k3n8v6"
Issue

↓

Design

↓

Implementation

↓

Test

↓

Evaluation

↓

Memory Update
```

---

# 10. AI開発Memory

保存場所：

```text id="s6m4x8"
memory/development/
```

---

保存：

- 技術判断
- 変更理由
- 問題
- 解決策

---

# 11. 最初の実装タスク一覧

Priority順：

```text
1. Repository Setup
2. Memory Manager
3. Orchestrator
4. Evaluation Engine
5. Primitive Framework
6. Skill Framework
7. Workflow Engine
8. API
9. POC
```

---

# 12. 完成判定

Claude Code開発終了条件：

```text id="t5n9m2"
✓ POCが動作する

✓ 思考Traceが残る

✓ 判断理由が残る

✓ 評価できる

✓ Memoryを再利用できる
```

---

# 13. 最終定義

Insight Synapse Claude Code Execution Planとは、

> AI開発エージェントと人間が協調し、設計思想を維持しながら知的システムを構築するための開発実行計画である。

Claude Codeの役割は、

コードを書くことではない。

**Insight Synapseという知能構造を、一緒に育てること。**