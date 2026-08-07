"""Orchestrator — 次Actionの判断制御。

正版: docs/03_コアコンポーネント/02_オーケストレーター仕様書.md
数値正版: docs/03_コアコンポーネント/00_数値定義書.md §3.4・§3.5

State を読み、次に取るべき Action を決定論的に返す（Claude は呼ばない）。
- 棄権（abstain）: confidence < 0.3 OR unknown_level >= 0.7 → 判断を保留し調査へ
- 探索（explore）: unknown_level >= 0.6 → Explore / Research 優先
- 制作（create）: confidence >= 0.75 かつ unknown_level <= 0.25 → Create へ
- 判断保留（otherwise）: 情報収集・代替案検討
"""

from __future__ import annotations

from dataclasses import dataclass

from core.state import Action, State


@dataclass
class Decision:
    """Orchestrator の判断結果。"""

    action: Action
    reason: str
    confidence: float
    unknown_level: float


class Orchestrator:
    def __init__(
        self,
        *,
        abstain_confidence_lt: float = 0.3,
        abstain_unknown_level_ge: float = 0.7,
        explore_unknown_level_ge: float = 0.6,
        create_confidence_ge: float = 0.75,
        create_unknown_level_le: float = 0.25,
    ):
        self.abstain_confidence_lt = abstain_confidence_lt
        self.abstain_unknown_level_ge = abstain_unknown_level_ge
        self.explore_unknown_level_ge = explore_unknown_level_ge
        self.create_confidence_ge = create_confidence_ge
        self.create_unknown_level_le = create_unknown_level_le

    def decide(self, state: State) -> Decision:
        """State を読み、次Actionを決定する。順序: 棄権 → 探索 → 制作 → 保留。"""
        state.refresh_derived()
        conf = state.confidence
        ul = state.unknown_level

        # 1. 棄権機構（03/00 §3.5）: 不確実性が高い状態で推測による判断を禁止
        if conf < self.abstain_confidence_lt or ul >= self.abstain_unknown_level_ge:
            state.judgment = "abstain"
            state.available_actions = ["explore"]
            return Decision(
                action="abstain",
                reason=(
                    f"confidence {conf:.2f} < {self.abstain_confidence_lt} または "
                    f"unknown_level {ul:.2f} >= {self.abstain_unknown_level_ge} のため判断を保留"
                ),
                confidence=conf,
                unknown_level=ul,
            )

        state.judgment = "normal"

        # 2. 探索継続（03/00 §3.4）
        if ul >= self.explore_unknown_level_ge:
            state.available_actions = ["explore", "create"]
            return Decision(
                action="explore",
                reason=f"unknown_level {ul:.2f} >= {self.explore_unknown_level_ge} のため探索を優先",
                confidence=conf,
                unknown_level=ul,
            )

        # 3. 制作開始（03/00 §3.4）
        if conf >= self.create_confidence_ge and ul <= self.create_unknown_level_le:
            state.available_actions = ["create"]
            return Decision(
                action="create",
                reason=(
                    f"confidence {conf:.2f} >= {self.create_confidence_ge} かつ "
                    f"unknown_level {ul:.2f} <= {self.create_unknown_level_le} のため制作へ"
                ),
                confidence=conf,
                unknown_level=ul,
            )

        # 4. 判断保留（情報収集・代替案検討）
        state.available_actions = ["explore", "create"]
        return Decision(
            action="explore",
            reason=f"confidence {conf:.2f}・unknown_level {ul:.2f} が境界帯域のため情報収集を優先",
            confidence=conf,
            unknown_level=ul,
        )
