"""タスク定義 — AIサービス企画ドメインの評価タスクセット。

正版: docs/11_実装計画とロードマップ/09_最初の動く試作品設計書.md

実験は「新しいAIサービスを考えたい」という不確実な企画意図に対し、
Target（対象顧客）・Value（提供価値）・Risk（リスク）・Opportunity（機会）の
4観点を明示した分析成果物を生成させる。このタスクは unknown が豊富に発生する
ドメインであり、C4（unknown管理 + Orchestrator制御）の効果を測定するのに適している。

- dev_set（5問）: 開発用。ハーネスの動作確認・テスト駆動に使う
- prod_set（20問）: 本番実験用（Step 1 の N=20/条件）
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class POCTask:
    """1問の評価タスク。"""

    id: str          # e.g. "dev-01", "prod-01"
    theme: str       # タスクテーマ（日本語）
    prompt: str      # 完成済みプロンプト（テンプレート展開済み）


_PROMPT_TEMPLATE = """あなたはAIサービス企画の専門家です。以下のテーマについて、
Target（対象顧客）・Value（提供価値）・Risk（リスク）・Opportunity（機会）の観点から分析してください。

テーマ：{theme}

分析は具体的に。どのような顧客が、どのような価値を得て、何がリスクで、
どのような機会があるのかを、整合的で実行可能性のある形で記述してください。"""


def _task(task_id: str, theme: str) -> POCTask:
    return POCTask(id=task_id, theme=theme, prompt=_PROMPT_TEMPLATE.format(theme=theme))


# ---- 開発用タスクセット（5問） ----
DEV_THEMES: list[str] = [
    "日々の健康状態を記録し、生活改善のきっかけを与えるパーソナル健康AI",
    "料理初心者向けに冷蔵庫の中身から献立を提案する家計AI",
    "個人の学習履歴から最適な復習タイミングを提案する学習支援AI",
    "ペットの食事・体調を記録し、異常を早期に気づかせるペットケアAI",
    "日々の雑務を音声でまとめて処理するパーソナル秘書AI",
]

# ---- 本番用タスクセット（20問） ----
PROD_THEMES: list[str] = [
    "高齢者の服薬管理を支援し、飲み忘れを防ぐ見守りAI",
    "中小企業の請求書処理を自動化する経理AI",
    "地方自治体の住民相談窓口を効率化する行政AI",
    "子育て中の親向けに子どもの成長記録を整理する育児AI",
    "不動産投資の物件選定をサポートする投資判断AI",
    "フリーランス向けに請求・確定申告を一元管理する事業支援AI",
    "在宅勤務者の集中力維持をサポートするタスク管理AI",
    "アレルギーを持つ人向けに食品成分を解析する食事サポートAI",
    "製造現場の機械学習モデルの運用監視を支援する保守AI",
    "英語学習者向けに発音をリアルタイム評価する会話練習AI",
    "カーボンニュートラルを目指す企業の排出量可視化を支援する環境AI",
    "精神的なストレスを記録し、セルフケアを提案するメンタルケアAI",
    "スポーツ愛好家向けにフォームを動画から分析するトレーニングAI",
    "失語症の方の会話を支援するコミュニケーションAI",
    "地方の農家向けに気象データから栽培管理を支援する農業AI",
    "親の介護負担を軽減する介護記録・連携AI",
    "Eコマース事業者向けに在庫需要を予測する販売管理AI",
    "言語聴覚士の業務記録を自動化する医療記録AI",
    "旅行者の言語バリアを解消するリアルタイム翻訳AI",
    "中小企業の採用活動を効率化する採用支援AI",
]


def dev_tasks() -> list[POCTask]:
    """開発用タスクセット（5問）。"""
    return [_task(f"dev-{i:02d}", theme) for i, theme in enumerate(DEV_THEMES, start=1)]


def prod_tasks() -> list[POCTask]:
    """本番用タスクセット（20問）。"""
    return [_task(f"prod-{i:02d}", theme) for i, theme in enumerate(PROD_THEMES, start=1)]


def taskset(name: str) -> list[POCTask]:
    """名前付きタスクセットを返す。"dev" → 開発用、"prod" → 本番用。"""
    if name == "dev":
        return dev_tasks()
    if name == "prod":
        return prod_tasks()
    raise ValueError(f"不明なタスクセット名: {name!r}（'dev' または 'prod'）")


def head_tasks(n: int, name: str = "dev") -> list[POCTask]:
    """先頭 n 問を返す。--tasks=N オプション用。"""
    return taskset(name)[:n]
