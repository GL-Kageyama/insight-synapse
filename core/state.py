"""State Object — Insight Synapse の現在状態（15フィールド）。

正版: docs/03_コアコンポーネント/01_状態モデル仕様書.md §3-§4
数値正版: docs/03_コアコンポーネント/00_数値定義書.md §3（unknown_level / confidence / 棄権）

Stateは「AIが現在どのような認識状態にあり、次にどのような思考行動を取るべきかを
判断するための内部状態」。思考を状態遷移の連続として扱う。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

# 標準フェーズ（03/01 状態モデル仕様書）: observe → understand → explore → design → create → evaluate → improve
Phase = Literal["observe", "understand", "explore", "design", "create", "evaluate", "improve"]
UnresolvedStatus = Literal["unresolved", "partial", "resolved"]
Judgment = Literal["normal", "abstain"]
Action = Literal["explore", "create", "abstain", "complete"]


@dataclass
class UnknownItem:
    """未知項目（質的）。算出をトレーサブルにするための構造。"""

    item: str
    importance: float = 0.5  # 重要度（0〜1）
    status: UnresolvedStatus = "unresolved"


@dataclass
class Hypothesis:
    """仮説。confidence 統合に使う。"""

    statement: str
    confidence: float = 0.5  # 仮説の確信度（0〜1）


@dataclass
class State:
    """State Object — 15フィールド。

    フィールド:
        id, goal, context, phase, known, unknown, unknown_level,
        hypotheses, constraints, confidence, judgment, active_question,
        available_actions, history, timestamp
    """

    id: str
    goal: str
    context: str = ""
    phase: Phase = "observe"
    known: list[str] = field(default_factory=list)
    unknown: list[UnknownItem] = field(default_factory=list)
    unknown_level: float = 0.0
    hypotheses: list[Hypothesis] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    confidence: float = 0.0
    judgment: Judgment = "normal"
    active_question: str = ""
    available_actions: list[Action] = field(default_factory=list)
    history: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: _now_iso())

    # ---- 導出量 ----

    def compute_unknown_level(self) -> float:
        """unknown_level（量的）。03/00 §3.2 の重要度加重平均。

        unknown_level = Σ(重要度_i × 未解決度_i) ÷ Σ(重要度_i)

        未解決度: resolved=0, partial=0.5, unresolved=1（03/00 の二値式を
        3値ステータスに運用拡張。partialは中間扱い）。
        """
        if not self.unknown:
            return 0.0
        total_weight = 0.0
        unresolved_sum = 0.0
        for u in self.unknown:
            total_weight += u.importance
            unresolved_sum += u.importance * _unresolved_degree(u.status)
        if total_weight == 0:
            return 0.0
        return unresolved_sum / total_weight

    def compute_confidence(self) -> float:
        """confidence（0〜1）。03/00 §3.3。

        仮説が無い場合: confidence = 1 − unknown_level
        仮説がある場合: confidence = 0.5 × (1 − unknown_level) + 0.5 × mean(hypotheses.confidence)
        """
        base = 1.0 - self.unknown_level
        if not self.hypotheses:
            return base
        mean_hyp = sum(h.confidence for h in self.hypotheses) / len(self.hypotheses)
        w = 0.5  # hypothesis_weight（03/00 §3.3、params.yaml と整合）
        return w * base + w * mean_hyp

    def refresh_derived(self) -> "State":
        """導出量（unknown_level / confidence）を再計算して更新。"""
        self.unknown_level = self.compute_unknown_level()
        self.confidence = self.compute_confidence()
        return self

    # ---- 棄権機構（03/00 §3.5）----

    def should_abstain(self, *, confidence_lt: float = 0.15, unknown_level_ge: float = 0.85) -> bool:
        """棄権条件。いずれかを満たせば判断を下さず明示的に棄権。

        - confidence < confidence_lt（既定 0.15）
        - unknown_level >= unknown_level_ge（既定 0.85）

        Step 2 較正（2026-08-08）: 旧値 0.3 / 0.7 は AIサービス企画ドメインの
        初期 unknown_level（0.74-0.92）で全試行 abstain になったため、
        config/params.yaml の `abstention` と整合させて 0.15 / 0.85 に再設定。
        """
        return self.confidence < confidence_lt or self.unknown_level >= unknown_level_ge

    # ---- 探索ループの State 反映（03/00 §3.4 / 11/09 §13）----

    def resolve_unknown(self, item: str, status: UnresolvedStatus) -> "State":
        """探索結果を未知項目に反映する。

        - status="resolved": unknown を unknown リストに残したまま status="resolved" にする
          （03/00 §3.2 の式では resolved は分子に 0、分母には重要度として残る。
          remove すると分母からも消え unknown_level が相対値のまま下がらないため）
        - status="partial": 未解決度 1.0 → 0.5（confidence 計算に反映）
        - 対象 item が見つからない場合は何もしない（該当なし）
        """
        for u in self.unknown:
            if u.item == item:
                u.status = status
                self.refresh_derived()
                return self
        return self

    def add_known(self, item: str) -> "State":
        """探索で得られた既知事項を known に追加（重複はスキップ）。"""
        if item and item not in self.known:
            self.known.append(item)
        return self

    def add_hypothesis(self, statement: str, confidence: float = 0.5) -> "State":
        """探索で得られた仮説を hypotheses に追加（confidence 計算に反映）。"""
        if statement:
            self.hypotheses.append(Hypothesis(statement=statement, confidence=_clamp01(confidence)))
            self.refresh_derived()
        return self

    def apply_abstention(
        self, *, confidence_lt: float = 0.15, unknown_level_ge: float = 0.85, reason: str = ""
    ) -> "State":
        """棄権機構を適用。条件を満たす場合 judgment="abstain" にし、Reasonを履歴に残す。

        棄権は「無回答」ではなく「保留理由を伴う判断停止」。代替案の検討・調査を優先する。
        """
        self.refresh_derived()
        if self.should_abstain(confidence_lt=confidence_lt, unknown_level_ge=unknown_level_ge):
            self.judgment = "abstain"
            self.history.append(f"ABSTAIN: {reason or 'confidence/unknown_level が棄権閾値に達した'}")
        else:
            self.judgment = "normal"
        return self

    # ---- 直列化 ----

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_yaml(self) -> str:
        import yaml

        return yaml.safe_dump(self.to_dict(), allow_unicode=True, sort_keys=False)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "State":
        known = data.get("known", [])
        unknown = [UnknownItem(**u) if isinstance(u, dict) else u for u in data.get("unknown", [])]
        hypotheses = [Hypothesis(**h) if isinstance(h, dict) else h for h in data.get("hypotheses", [])]
        return cls(
            id=data["id"],
            goal=data["goal"],
            context=data.get("context", ""),
            phase=data.get("phase", "observe"),
            known=known,
            unknown=unknown,
            unknown_level=data.get("unknown_level", 0.0),
            hypotheses=hypotheses,
            constraints=data.get("constraints", []),
            confidence=data.get("confidence", 0.0),
            judgment=data.get("judgment", "normal"),
            active_question=data.get("active_question", ""),
            available_actions=data.get("available_actions", []),
            history=data.get("history", []),
            timestamp=data.get("timestamp", _now_iso()),
        )

    @classmethod
    def from_yaml(cls, text: str) -> "State":
        import yaml

        return cls.from_dict(yaml.safe_load(text))

    def save_to(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_yaml(), encoding="utf-8")


def _unresolved_degree(status: UnresolvedStatus) -> float:
    return {"resolved": 0.0, "partial": 0.5, "unresolved": 1.0}[status]


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_state(
    goal: str,
    *,
    known: Optional[list[str]] = None,
    unknown: Optional[list[UnknownItem]] = None,
    context: str = "",
    phase: Phase = "observe",
) -> State:
    """導出量を計算済みのStateを生成するファクトリ。"""
    st = State(
        id=f"state-{_now_iso().replace(':', '')}",
        goal=goal,
        context=context,
        phase=phase,
        known=known or [],
        unknown=unknown or [],
    )
    st.refresh_derived()
    return st
