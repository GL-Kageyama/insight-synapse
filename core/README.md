# core/

Insight Synapseの中枢。**状態管理・判断・制御**を担当する。

> **正版**: `docs/03_コアコンポーネント/00_数値定義書.md`（数値）・`docs/03_コアコンポーネント/01_状態モデル仕様書.md`（State Schema）・`docs/03_コアコンポーネント/02_オーケストレーター仕様書.md`

**現在の状態**: 骨格のみ（POC実装フェーズで充填）

| ディレクトリ | 責務 |
|---|---|
| `schemas/` | コア抽象層（Runtime非依存の正版）。State / Trace / Evaluation |
| `orchestrator/` | 次Action判断・Skill選択・Agent呼出判断（最重要） |
| `state/` | 状態管理（State Object・unknown管理・confidence・棄権機構） |
| `decision/` | 判断（判断はCoreへ — 開発原則 Rule 2） |
