# Insight Synapse
## Human Interface MVP Specification
### ヒューマンインターフェースMVP仕様書 v0.1

---

# 1. 目的

本ドキュメントは、Insight Synapseにおける人間とAIの協調インターフェース設計を定義する。

目的：

> AIの処理結果だけを見るのではなく、思考状態・判断理由・改善過程を人間が理解し、介入できる環境を作る。

---

# 2. 基本思想

一般的AI UI：

```text id="s0a1x8"
Input

↓

AI処理

↓

Output
```

---

Insight Synapse UI：

```text id="e7f9k3"
Goal

↓

AI State

↓

Decision

↓

Execution

↓

Evaluation

↓

Memory

↓

Improvement
```

---

# 3. MVP設計方針

最初は軽量にする。

不要：

- 高度な3D表示
- 複雑なグラフ
- 大規模管理画面

必要：

- 状態確認
- 思考履歴確認
- 判断確認
- 承認操作

---

# 4. MVP UI構成

```text id="h4p9d2"
Insight Synapse UI

├── Chat Interface

├── Current State View

├── Thought Trace Viewer

├── Decision Panel

└── Memory Viewer
```

---

# 5. Chat Interface

## 役割

人間との基本入力窓。

---

機能：

- Goal入力
- 指示
- 質問
- 修正要求

---

例：

```text id="v3j7q1"
User:

新しいサービス案を作りたい


AI:

現在の状態を分析します。
```

---

# 6. Current State View

## 役割

AIの現在位置を表示する。

---

表示：

```yaml id="m7x2z4"
Goal:
サービス設計

Phase:
Explore

Confidence:
0.45

Unknown:
0.70

Next Action:
Research
```

---

# 7. Thought Trace Viewer

## 最重要UI

AIの思考軌跡を見る。

---

表示：

```markdown id="c8r4n6"
# Thought Trace


Question:

本当に必要な機能は何か


Analysis:

ユーザー課題の理解不足


Decision:

追加調査を実施
```

---

目的：

- ブラックボックス化防止
- 人間との協調
- 改善材料

---

# 8. Decision Panel

## 役割

重要判断を確認する。

---

表示：

```text id="k5v9b3"
Decision:

Use Research Workflow


Reason:

Unknown is high


Confidence:

0.65


Approval:

[Accept]

[Modify]

[Reject]
```

---

# 9. Human Approval Flow

重要処理では承認を挟む。

---

流れ：

```text id="w2m6c8"
AI Proposal

↓

Human Review

↓

Approve

↓

Execute
```

---

# 10. Memory Viewer

## 役割

AIの経験を見る。

---

表示：

```text id="p6n1s4"
Past Pattern:

Similar project succeeded with:

Research

↓

Structure

↓

Critique

↓

Create
```

---

# 11. MVP技術構成

最小構成：

```text id="y8c3m5"
Frontend:

Simple Web UI


Backend:

API Server


Storage:

Markdown Files

+

Git
```

---

# 12. Markdown First設計

初期ではDBを必須にしない。

理由：

- 可読性
- 編集容易性
- Git管理
- Claude Codeとの相性

---

構造：

```text id="n9x5w7"
workspace/

├── state.md

├── trace.md

├── decisions.md

└── memory/
```

---

# 13. 人間の役割

Humanは、

「全部指示する存在」

ではない。

---

役割：

```text id="r3m7p2"
Goal設定

↓

価値判断

↓

重要判断承認

↓

方向修正
```

---

# 14. AIの役割

AI：

- 探索
- 分析
- 制作
- 評価
- 改善提案

---

# 15. UI設計原則

## Principle 1

結果より過程を見る。

---

## Principle 2

AI判断を説明可能にする。

---

## Principle 3

人間介入ポイントを明確化する。

---

## Principle 4

情報量を増やしすぎない。

---

# 16. MVP画面イメージ

```text
--------------------------------

Goal

AIサービス設計


Current Phase

[Research]


Decision

追加調査を実行します


Reason

不確実性が高いため


Trace

過去5ステップ表示


Memory

関連Pattern 3件


[Approve]

--------------------------------
```

---

# 17. 将来拡張

## Visual Thinking Map

思考構造を可視化。

---

## Agent Dashboard

Agent活動表示。

---

## Workflow Graph

処理経路表示。

---

## Collaboration Mode

複数人＋AI協働。

---

# 18. MVP成功条件

以下が確認できれば成功。

```text id="q4z8n1"
人間が、

1. AIの状態を理解できる

2. 判断理由を確認できる

3. 修正指示できる

4. 改善履歴を追える
```

---

# 19. 最終アーキテクチャ

```text id="u7k3p5"
Human

↓

Interface

↓

Orchestrator

↓

Workflow

↓

Skill / Agent

↓

Evaluation

↓

Memory

↓

Interface Feedback
```

---

# 20. 最終定義

Insight Synapse Human Interfaceとは、

> AIの出力を見るだけではなく、AIの思考状態・判断過程・成長履歴を人間と共有し、協調的に知能を形成するためのインターフェースである。

最初のUIの目的は、

**AIを操作することではなく、AIと一緒に考えること**

である。