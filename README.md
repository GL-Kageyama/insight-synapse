# insight-synapse

A cognitive architecture framework for AI that continuously improves its own thinking, not just generates answers. Treats thinking as state transitions, with Thought Trace-centric memory, explicit unknown management, and evaluate→improve loops. Humans are direction-setters. 37 design specs in Markdown, verified via POC controlled experiments.

---

# Insight Synapse

**「より速く答えるAI」ではなく、「考え方を自ら改善し続けるAI」** を作るための、認知アーキテクチャフレームワークの設計リポジトリ。

単に回答や成果物を出すだけでなく、AI自身の**思考状態・判断過程・評価・改善**を管理対象にする。思考を「目的に向かって状態を変化させる処理」と捉え、その**思考経路そのもの**を再利用可能な知識にしようとするのが全体の狙いです。

> このリポジトリの中心はコードではない。中心にあるものは、**AIが成長するための構造設計**である。

---

## 1. What is Insight Synapse

Insight Synapseは、AIを「生成ツール」としてではなく、「思考・判断・制作・評価・改善を循環させる知的アーキテクチャ」として実装するための設計書群です。

設計を貫く5つの考え方。

1. **思考 = 状態変化** — 思考は文章生成ではなく、状態を目的に近づける変換処理
2. **責務分離** — 判断 / 実行 / 記憶 / 評価 / 改善 をレイヤー分離
3. **思考の軌跡を中心とした記憶** — 「何を知っていたか」ではなく「どう考えたか」を保存
4. **評価は改善のため** — 採点が目的ではなく、次に改善すべき点を発見する
5. **人間は方向調整者** — 作業者ではなく、方向を調整する立場

主要コンポーネントは **State / Orchestrator / Skill / Primitive / Memory / Evaluation / Learning** の7つ。実行基盤は **Claude Code**（Markdown + YAML + Git + Skillシステム）を第一ターゲットとし、小さく検証しながら段階的に拡張していきます。

### 現在の状態

- ✅ `docs/` — 設計仕様書群（37本）をコミット済み。Wisdom Council評価に基づく改訂履歴は `docs/README.md` に記録
- ✅ リポジトリ骨格 — 10/02最終構成の12レイヤーを整備済み。各レイヤーの責務と正版参照は各 `README.md` に記載
- ✅ **POC Step 1 実装**（`core/`・`evaluation/`・`memory/`・`poc/`）— 仮説Hの対照実験（B0 vs C4）が実行可能な最初の動く試作品。単体テスト37件通過・モックスモークラン動作確認済み。正式版コードの実装基盤（最終構成は `10_環境とリポジトリ/02_最終リポジトリ構成仕様書.md` が正版）

---

## 2. Architecture

システムは「機能別」ではなく**「知能構造別」**に分割する。

```text
Thinking → Planning → Execution → Evaluation → Learning
```

システムの基本フロー。

```text
Goal
 ↓
Workflow Engine ──→ Orchestrator ──→ State管理 ──→ Skill / Primitive ──→ 実行
                                                                            ↓
                        Memory ←──── Learning ←──── Evaluation ←────────────┘
```

最終システム構造。

```text
Human
 ↓
Interface
 ↓
Orchestrator
 ↓
Workflow Engine
 ↓
Skill Layer
 ↓
Primitive Layer
 ↓
Execution
 ↓
Evaluation Engine
 ↓
Memory System
 ↓
Improved Intelligence
```

### 最終ディレクトリ構成（正版: `10_環境とリポジトリ/02_最終リポジトリ構成仕様書.md`）

```text
insight-synapse/
├── .claude/          ← Skill起動・開発補助の入口
├── core/             ← 状態管理・判断・制御（中枢）
│   └── schemas/      ← コア抽象（State / Trace / Evaluation。Runtime非依存の正版）
├── adapters/         ← コア抽象と特定Runtimeの変換（第一: claude-code/）
├── workflows/        ← 目的達成までの流れ（creation / research / problem-solving / learning）
├── skills/           ← 再利用可能な能力（cognitive / creation / evaluation / communication）
├── primitives/       ← 最小思考操作（分解・比較・抽象化・再枠組・生成・統合・評価・省察）
├── agents/           ← 専門判断主体（evaluator / researcher / specialist）
├── evaluation/       ← 評価基準・検証問題・評価結果
├── memory/           ← 状態・思考軌跡・判断履歴・パターン・外部知識
├── governance/       ← 権限管理・判断ルール・変更履歴
├── interface/        ← API・Web
├── tests/
├── docs/             ← 設計仕様書群（37本）
└── README.md
```

依存方向は「アダプタ → コア抽象」のみ。コア抽象はRuntimeの詳細を知らない。

### ドキュメント構成

`docs/` は構想（なぜ）→ 設計（どういう構造）→ 仕様（実装の詳細）→ 計画（いつ・どう作る）の順に読める11カテゴリ構成。全ファイル一覧は `docs/README.md` を参照。

| カテゴリ | 内容 | 資料が答えている問い |
|---|---|---|
| **01 コンセプトと哲学** | 全体枠組み・設計原則・開発ポリシー | なぜ作るのか / 何を作るのか |
| **02 アーキテクチャ** | システム・マルチエージェント・統合構造 | 全体はどう組み上がるのか |
| **03 コアコンポーネント** | 状態モデル・オーケストレーター・プリミティブ・思考コスト | 思考の中核はどう動くのか |
| **04 スキルとワークフロー** | 能力・思考手順 | 何ができて・どう進めるのか |
| **05 メモリー** | 思考軌跡の保存 | 過去をどう活かすのか |
| **06 評価と学習** | 評価・改善ループ | どう成長するのか |
| **07 インターフェースとAPI** | 人間との接点 | 人はどう関わるのか |
| **08 データと技術仕様** | 技術仕様・データモデル・ユースケース | 実装の詳細は何か |
| **09 セキュリティ** | 安全・ガバナンス | 安全に動かすには |
| **10 環境とリポジトリ** | 開発環境・リポジトリ構成 | どこで動かすのか |
| **11 実装計画とロードマップ** | MVP・POC・Claude Code実装・段階計画 | いつ・どう作るのか |

---

## 3. Quick Start

成果物は**設計仕様書群**と、仮説Hを実証するための**POC Step 1 実装**（`core/`・`poc/`）です。

### まず読むべき文書

- **全体像だけ掴みたい** → `docs/01_コンセプトと哲学/01_AI思考アーキテクチャフレームワーク.md`（概要仕様書）を最初に
- **設計を理解したい** → `docs/02_アーキテクチャ/` → `docs/03_コアコンポーネント/` → `docs/04_スキルとワークフロー/` → `docs/05_メモリー/` → `docs/06_評価と学習/` の順
- **実装を始めたい** → `docs/11_実装計画とロードマップ/`（ロードマップ・最初の実装タスク・POC）→ `docs/10_環境とリポジトリ/` → `docs/08_データと技術仕様/`

### POC Step 1 を実行する（仮説Hの対照実験）

POCは `docs/11_実装計画とロードマップ/09_最初の動く試作品設計書.md` に基づく、B0（単純指示） vs C4（Insight Synapse）の成功率対照実験。数値は全て `config/params.yaml`（正版: `docs/03_コアコンポーネント/00_数値定義書.md`）から供給される。

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...          # 実実行はAPIキー必須

python main.py --all --tasks=5 --mock     # API不要のスモークラン（パイプライン検証）
python main.py --all --tasks=20           # 本番: 20問×全条件（B0/C4）
```

### 正版文書（Single Source of Truth）

数値・構造の正版は以下の1本に集約され、他文書は参照のみ。改訂は正版の更新から行う。

- 数値定義（評価5軸・しきい値・Cost式・Confidence/Unknown算出・棄権機構）: `docs/03_コアコンポーネント/00_数値定義書.md`
- State Schema: `docs/03_コアコンポーネント/01_状態モデル仕様書.md`
- Thought Trace Schema: `docs/05_メモリー/01_メモリーアーキテクチャ仕様書.md`
- Evaluation Schema: `docs/06_評価と学習/01_エバリュエーションエンジン詳細仕様書.md`
- リポジトリ構成: `docs/10_環境とリポジトリ/02_最終リポジトリ構成仕様書.md`
- POC実験設計: `docs/11_実装計画とロードマップ/09_最初の動く試作品設計書.md`

---

## 4. Development

### Git運用

1つの判断（Decision）に対して1コミット。コミットメッセージには意図（Reason）を添える。

```text
Add creation workflow

Reason:
Improve reusable production flow
```

### 初期実装順序（正版: `docs/10_環境とリポジトリ/02` §10）

1. **Memory** — 思考履歴保存
2. **Orchestrator** — 判断制御
3. **Evaluation** — 改善循環
4. **Skill** — 能力追加
5. **Workflow** — 流れ管理
6. **Interface** — 可視化

MVPは最小構成から始める（最初から全部作らない）。

### 開発原則

- **Rule 1**: Layer間の責務を混ぜない
- **Rule 2**: 判断はCoreへ
- **Rule 3**: 能力はSkillへ
- **Rule 4**: 経験はMemoryへ
- **Rule 5**: 改善はEvaluationから始める

### ライセンス

[MIT License](./LICENSE) — Copyright (c) 2026 GL-Kageyama

---

## 5. Philosophy

AIがこの先もずっと「答えを出す道具」のままでよいのか。Insight Synapseは、そう問い直すところから始まっています。

思考は一次的な文章出力ではなく、**蓄積・再利用できる資産**です。その資産を管理・評価・改善する構造があれば、AIは使えば使うほど考え方を洗練させていける。この設計の最終定義は次の通りです。

> Insight Synapse Repositoryとは、AIを単なる生成ツールとして実装するのではなく、思考・判断・制作・評価・改善を循環させる知的アーキテクチャとして管理するための開発基盤である。

ただし、この構想の有効性はまだ**実証されていません**。受益者物語（`docs/08_データと技術仕様/03_ユースケース設計書.md` §14）は正当化ではなく探索仮説であり、POC対照実験（`docs/11_実装計画とロードマップ/09`）で評価者の独立性・統計的キャリブレーションを踏まえて検証する対象です。次の成果物は設計文書ではなく、実証データです。
