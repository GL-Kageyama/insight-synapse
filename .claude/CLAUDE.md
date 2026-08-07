# CLAUDE.md

## このリポジトリの目的

**Insight Synapse** — 「答えを生成するAI」ではなく「考え方を自ら改善し続けるAI」を作るための認知アーキテクチャフレームワーク。

このリポジトリは設計仕様書群（`docs/`）と、その正式版コード（`core/` 以下）を管理する開発基盤。

## 正版文書（Single Source of Truth）

数値・構造・スキーマの正版は以下。改訂は正版の更新から行い、他文書は参照のみ。

- 数値定義（評価5軸・しきい値・Cost式・Confidence/Unknown・棄権機構）: `docs/03_コアコンポーネント/00_数値定義書.md`
- State Schema: `docs/03_コアコンポーネント/01_状態モデル仕様書.md` / `core/schemas/state.schema.yaml`
- Thought Trace Schema: `docs/05_メモリー/01_メモリーアーキテクチャ仕様書.md` / `core/schemas/trace.schema.yaml`
- Evaluation Schema: `docs/06_評価と学習/01_エバリュエーションエンジン詳細仕様書.md` / `core/schemas/evaluation.schema.yaml`
- リポジトリ構成: `docs/10_環境とリポジトリ/02_最終リポジトリ構成仕様書.md`
- POC実験設計: `docs/11_実装計画とロードマップ/09_最初の動く試作品設計書.md`

## 開発原則

- **Rule 1**: Layer間の責務を混ぜない
- **Rule 2**: 判断はCoreへ
- **Rule 3**: 能力はSkillへ
- **Rule 4**: 経験はMemoryへ
- **Rule 5**: 改善はEvaluationから始める

## Git運用

1つの判断（Decision）に1コミット。コミットメッセージには意図（Reason）を添える。

## 現在の状態

- ✅ 設計仕様書群（37本）・リポジトリ骨格（12レイヤー）をコミット済み
- ✅ POC Step 2（測定系較正）実装完了 — 閾値較正 / 探索ループ / ルーブリック改訂 / B1・B2 / 空応答再試行 / 停止条件・思考品質L1-L3
- 🔄 コンパクト本番（`--all --tasks=1 --taskset=prod`）実行中 → **次の作業ターゲットと見通しは `NEXT_STEPS.md` を参照**
