# Insight Synapse
## MVP Acceptance Criteria Specification
### MVP完成判定基準書 v0.1

---

# 1. 目的

本ドキュメントは、Insight Synapse MVPの完成条件を定義する。

目的：

> 最小構成で「思考・判断・評価・記憶・改善」の循環が成立していることを確認する。

---

# 2. MVPの定義

Insight Synapse MVPとは、

単なるAIチャットではない。

以下の循環を実行できる状態を指す。

```text id="a8k4m2"
Goal

↓

Understand

↓

Think

↓

Decide

↓

Create

↓

Evaluate

↓

Memory

↓

Improve
```

---

# 3. MVP必須機能

## 3.1 Goal Input

### 目的

人間から目的を受け取る。

---

必須：

- Goal入力可能
- Goal識別可能
- Goal保存可能

---

完成条件：

```text id="r3m7x5"
入力した目的が後工程で参照できる
```

---

## 3.2 State Management

### 目的

AIの現在状態を管理する。

---

管理項目：

```yaml id="k8p2m4"
goal:

phase:

confidence:

unknown_level:

next_action:
```

---

完成条件：

```text id="w5n9q1"
AIが現在状況を説明できる
```

---

## 3.3 Orchestrator

### 目的

次の行動を判断する。

---

必要能力：

- 状況分析
- Workflow選択
- Skill選択

---

完成条件：

```text id="m4x8v2"
なぜこの行動を選択したか説明できる
```

---

## 3.4 Workflow Engine

### 目的

処理手順を管理する。

---

最低Workflow：

```text id="p7m3q8"
Research

↓

Create

↓

Evaluate
```

---

完成条件：

```text id="c9n5x4"
目的に応じた処理フローを実行できる
```

---

## 3.5 Skill System

### 目的

能力を再利用する。

---

MVP Skill：

```text
question
analyze
structure
create
evaluate
reflect
```

---

完成条件：

```text id="z6m4p9"
Skillを追加・変更可能
```

---

## 3.6 Primitive System

### 目的

思考操作を構成する。

---

最低Primitive：

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

完成条件：

```text id="y5n2v8"
SkillがPrimitiveを組み合わせて動作する
```

---

## 3.7 Evaluation Engine

### 目的

成果物を評価する。

---

評価軸：

```text id="f4m9x2"
Quality

Logic

Creativity

Value

Risk
```

---

完成条件：

```text id="b7p3k8"
評価結果から改善案を生成できる
```

---

## 3.8 Memory System

### 目的

経験を保存する。

---

保存：

```text id="n6q2m5"
Thought Trace

Decision

Evaluation

Pattern
```

---

完成条件：

```text id="s8m4v1"
過去経験を次回判断に利用できる
```

---

# 4. End-to-End Acceptance Test

## テストテーマ

例：

```text id="x3k7m9"
新しいサービス案を考える
```

---

実行：

```text id="j5p8n2"
Goal Input

↓

State Analysis

↓

Orchestrator Decision

↓

Workflow Execution

↓

Skill Execution

↓

Artifact Creation

↓

Evaluation

↓

Memory Save
```

---

# 5. 合格条件

以下を満たすこと。

## Functional

```text id="q4m8z2"
✓ 動作する

✓ データ保存できる

✓ 結果を取得できる
```

---

## Intelligence

```text id="v7n3m5"
✓ 判断理由がある

✓ 評価できる

✓ 改善案が出る
```

---

## Memory

```text id="c2x9p4"
✓ 思考履歴が残る

✓ パターン抽出できる

✓ 次回利用できる
```

---

# 6. MVPで実装しないもの

初期段階では除外。

```text id="m8q5r1"
× 完全自律Agent

× 複数AI社会

× 高度GUI

× 巨大Knowledge Graph

× 自己改造AI
```

---

# 7. MVP品質基準

## Explainability

判断理由が説明可能。

---

## Reproducibility

同じ条件で再現可能。

---

## Extensibility

後から拡張可能。

---

## Safety

人間が制御可能。

---

# 8. MVP完成後の評価

完成後に確認：

```text id="w9m3k6"
このシステムは、

単なる回答生成か？

それとも、

判断改善システムになっているか？
```

---

# 9. 次フェーズ移行条件

Phase 3（Practical System）へ進む条件：

```text
✓ End-to-End成功
✓ Memory蓄積確認
✓ Evaluation改善確認
✓ Human利用価値確認
```

---

# 10. 最終定義

Insight Synapse MVPとは、

> AIが答えを生成するだけではなく、目的を理解し、判断し、結果を評価し、その経験を次回へ活用できる最小の知的循環システムである。

完成基準は、

**機能数ではなく、知能循環が回ること。**