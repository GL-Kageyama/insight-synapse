"""Orchestrator の判断ロジック単体テスト。

検証対象: docs/03_コアコンポーネント/00_数値定義書.md §3.4・§3.5
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.orchestrator import Orchestrator
from core.state import UnknownItem, new_state


def make_orch() -> Orchestrator:
    return Orchestrator(
        abstain_confidence_lt=0.3,
        abstain_unknown_level_ge=0.7,
        explore_unknown_level_ge=0.6,
        create_confidence_ge=0.75,
        create_unknown_level_le=0.25,
    )


def state_with_unknown_level(level: float) -> object:
    """unknown_level を近似的に設定した State を作る。

    単一項目では unknown_level は 0 or 1 しか出ないため、複数項目で重みを調整する。
    """
    assert 0.0 <= level <= 1.0
    # 2項目で weight を分解: importance 比で level を作る
    # level = (w1*1 + w2*0)/(w1+w2) = w1/(w1+w2) より、w1 = level, w2 = 1-level
    st = new_state(
        goal="g",
        unknown=[
            UnknownItem(item="unresolved", importance=max(level, 1e-9), status="unresolved"),
            UnknownItem(item="resolved", importance=max(1.0 - level, 1e-9), status="resolved"),
        ],
    )
    st.refresh_derived()
    return st


def test_abstain_on_low_confidence():
    """confidence < 0.3 → abstain（high unknown_level 由来）"""
    st = state_with_unknown_level(0.9)
    d = make_orch().decide(st)
    assert d.action == "abstain"
    assert st.judgment == "abstain"


def test_abstain_on_high_unknown_level():
    st = state_with_unknown_level(0.8)
    d = make_orch().decide(st)
    assert d.action == "abstain"


def test_explore_on_unknown_level_ge_06():
    """unknown_level >= 0.6 → explore（confidence は 0.4 < 0.75 で create 条件を満たさない）"""
    st = state_with_unknown_level(0.6)
    d = make_orch().decide(st)
    assert d.action == "explore"


def test_create_when_confident():
    """confidence >= 0.75 かつ unknown_level <= 0.25 → create"""
    st = state_with_unknown_level(0.0)
    # unknown_level=0 → confidence=1.0
    d = make_orch().decide(st)
    assert d.action == "create"
    assert st.judgment == "normal"


def test_fallback_explore_in_boundary():
    """境界帯域（0.25 < unknown_level < 0.6）→ 判断保留として explore"""
    st = state_with_unknown_level(0.4)
    d = make_orch().decide(st)
    assert d.action == "explore"


def test_decision_records_reason():
    st = state_with_unknown_level(0.4)
    d = make_orch().decide(st)
    assert len(d.reason) > 0
    assert isinstance(d.reason, str)
