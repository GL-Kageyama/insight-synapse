# Insight Synapse
## MVP Implementation Specification
### MVP実装仕様書 v0.1

---

# 1. 目的

本ドキュメントは、Insight Synapseの最初の実装範囲、リポジトリ構成、開発順序を定義する。

目的：

> 完全なAIエージェントシステムを作るのではなく、思考・評価・改善の循環を最小構成で実証する。

---

# 2. MVPの定義

Insight Synapse MVPとは、

```text
Goal入力

↓

Orchestrator判断

↓

Skill実行

↓

成果物生成

↓

Evaluation

↓

Memory保存
```

という一連のループが動作する状態である。

---

# 3. MVPで作らないもの

初期段階では以下を作らない。

- 複雑なWeb UI
- 完全自律エージェント
- 独自LLM
- ベクトルDB
- 高度な強化学習
- 複雑なマルチエージェント制御
- コア抽象と単一Runtimeを結合した実装（単一Runtime依存）
  → 思考資産（State / Thought Trace / Evaluation結果）はRuntime非依存の構造で保存する

理由：

思考構造の検証を優先するため。さらに、Claude Code単一依存はプラットフォーム側の機能吸収に脆弱なため、
コア抽象（State / Trace / Evaluation）とアダプタ（実行系）を最初から分離して作る。

---

# 4. MVPコア構成

Insight Synapse MVPは、**コア抽象層**と**アダプタ層**に分離して構成する。

```text
Insight Synapse

├── コア抽象層（Runtime非依存）
│   ├── State Schema（現在状態の構造定義）
│   ├── Trace Schema（Thought Traceの標準フォーマット）
│   └── Evaluation Schema（評価5軸・算出式）
│
└── アダプタ層（Claude Code上で実行）
    ├── Orchestrator
    ├── Skill System
    ├── Primitive System
    ├── Memory System
    ├── Evaluation System
    └── Workflow System
```

コア抽象はデータ構造であり、特定Runtimeを知らない。実行系（Orchestrator〜Workflow）はアダプタとしてClaude Code上に実装する。

---

# 5. リポジトリ構成

```text
insight-synapse/

├── README.md

├── CLAUDE.md

├── config/

│   ├── policy.yaml
│   └── settings.yaml


├── core/

│   ├── schemas/          ← コア抽象（Runtime非依存の正版）

│   │   ├── state.schema.yaml
│   │   ├── trace.schema.yaml
│   │   └── evaluation.schema.yaml
│   │
│   ├── orchestrator/

│   │   ├── decision.md
│   │   └── rules.yaml
│   │
│   └── state/


├── adapters/

│   └── claude-code/      ← 第一アダプタ（実行系・Skillはここに実装）


├── skills/

│   ├── question/

│   ├── analyze/

│   ├── structure/

│   ├── create/

│   ├── evaluate/

│   └── reflect/


├── primitives/

│   ├── decompose.md

│   ├── compare.md

│   ├── abstract.md

│   ├── reframe.md

│   ├── generate.md

│   ├── synthesize.md

│   ├── evaluate.md

│   └── reflect.md


├── memory/

│   ├── current.md

│   ├── traces/

│   ├── decisions/

│   └── patterns/


├── evaluation/

│   ├── criteria.yaml

│   └── reports/


├── workflows/

│   ├── creation.yaml
│   └── (templates/ active/)


└── artifacts/
```

> **正版**：最終リポジトリ構成は `10_環境とリポジトリ/02_最終リポジトリ構成仕様書.md`。本節はMVP初期構成であり、Workflowはトップレベル `workflows/` に一元配置する（旧記述の core配下 `workflow/` は廃止）。コア抽象（`core/schemas/`）とアダプタ（`adapters/claude-code/`）の分離は §4・§10 に従う。

---

# 6. Claude Code用設定

## CLAUDE.mdの役割

Claude CodeにInsight Synapseの思想を理解させる。

内容：

```markdown
# Project

Insight Synapse


# Role

You are an Orchestrator-assisted AI system.


# Rules

- Always record thought trace
- Evaluate before finalizing
- Prefer reusable patterns
- Separate Skill and Primitive
```

---

# 7. 開発フェーズ

---

# Phase 1
## Memory実装

実装：

- Thought Trace
- Pattern Memory

---

成果：

経験利用可能。

---

# Phase 2
## 思考ループ実装

目的：

最小循環を作る。

実装：

```text
Input

↓

State生成

↓

Decision

↓

Output

↓

Trace保存
```

---

成果：

AIが判断理由付きで動く。

---

# Phase 3
## Evaluation追加

実装：

- 評価基準
- 評価結果保存
- 改善提案

---

成果：

自己改善ループ完成。

---

# Phase 4
## Skill Layer追加

実装：

```text
Question

Analyze

Structure

Create

Evaluate

Reflect
```

---

成果：

処理を分離できる。

---

# Phase 5
## Workflow追加

実装：

YAMLベースWorkflow。

---

成果：

用途変更可能な汎用構造。

---

# 8. 最初の動作例

入力：

```text
新しいAIサービス案を作りたい
```

---

State生成：

```yaml
goal:
AIサービス設計

phase:
unknown

confidence:
low
```

---

Orchestrator判断：

```yaml
action:
explore

reason:
情報不足
```

---

Skill実行：

```text
Explore Skill
```

---

評価：

```text
Concept quality:
0.8

Risk:
0.5
```

---

Memory保存：

```text
成功パターン:

初期設計では探索を優先する
```

---

# 9. MVPで重要なファイル

優先順位：

## 最重要

```
CLAUDE.md
```

AIの行動原則。

---

## 次点

```
policy.yaml
```

判断基準。

---

## 次点

```
current.md
```

現在状態。

---

## 次点

```
trace.md
```

思考履歴。

---

# 10. 技術選択

MVP：

```text
Language:

Markdown

YAML

Python(optional)


Execution:

Claude Code（第一アダプタ）


Storage:

Git
```

## Runtimeは「アダプタ」である

Runtime（Claude Code）は、コア抽象（State / Trace / Evaluation）を実装する**最初のアダプタ**である。

```text
コア抽象：State Schema / Trace Schema / Evaluation Schema（Runtime非依存）

アダプタ　：Claude Code（Markdown + YAML + Git + Skill）
```

将来のアダプタ：

```text
API Server（HTTP / JSON）

IDEプラグイン（エディタ内での思考経路表示）

Web UI（人間による閲覧・承認）
```

Claude Codeがプラットフォーム側で同等機能を吸収しても、コア抽象と蓄積した思考資産は維持される。

---

# 11. 成功判定

MVP成功条件：

## 条件1

AIが判断理由を説明できる。

---

## 条件2

思考履歴が保存される。

---

## 条件3

評価結果から改善案が出る。

---

## 条件4

別テーマでも同じ構造で動く。

---

# 12. 将来拡張

MVP後：

```text
MVP

↓

Tool Integration

↓

Multi Agent Evaluation

↓

Vector Memory

↓

Autonomous Workflow Generation

↓

AI Development Platform
```

---

# 13. 最終定義

Insight Synapse MVPとは、

> Claude Code上で動作する、思考・制作・評価・記憶・改善の循環を持った汎用AI制作フレームワークである。

最初に作るべきものは高度なAIではなく、

**AIが考えた過程を管理し、改善できる構造**

である。