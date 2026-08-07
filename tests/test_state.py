"""State Object の単体テスト。

検証対象: docs/03_コアコンポーネント/01_状態モデル仕様書.md §3-§4
             docs/03_コアコンポーネント/00_数値定義書.md §3
"""

import sys
from pathlib import Path

import pytest

# リポジトリルートを import パスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.state import Hypothesis, State, UnknownItem, new_state


def test_state_has_15_fields():
    st = new_state(goal="AIサービスの可能性を評価する")
    data = st.to_dict()
    # 必須15フィールド
    required = {
        "id", "goal", "context", "phase", "known", "unknown", "unknown_level",
        "hypotheses", "constraints", "confidence", "judgment", "active_question",
        "available_actions", "history", "timestamp",
    }
    assert required.issubset(data.keys())
    assert data["goal"] == "AIサービスの可能性を評価する"


def test_unknown_level_weighted_average():
    """03/00 §3.2: unknown_level = Σ(importance×unresolved) / Σ(importance)"""
    st = new_state(
        goal="g",
        unknown=[
            UnknownItem(item="市場の前提", importance=0.8, status="unresolved"),
            UnknownItem(item="競合の動向", importance=0.2, status="resolved"),
        ],
    )
    # (0.8×1 + 0.2×0) / (0.8+0.2) = 0.8
    assert st.unknown_level == pytest_approx(0.8)


def test_unknown_level_with_partial():
    """partial は中間扱い（0.5）とする運用拡張。"""
    st = new_state(
        goal="g",
        unknown=[
            UnknownItem(item="a", importance=1.0, status="partial"),
        ],
    )
    assert st.unknown_level == pytest_approx(0.5)


def test_unknown_level_empty_is_zero():
    st = new_state(goal="g")
    assert st.unknown_level == 0.0


def test_confidence_base_form():
    """03/00 §3.3 基本形: confidence = 1 − unknown_level"""
    st = new_state(
        goal="g",
        unknown=[UnknownItem(item="a", importance=1.0, status="unresolved")],
    )
    assert st.confidence == pytest_approx(0.0)  # 1 - 1.0
    st2 = new_state(
        goal="g",
        unknown=[UnknownItem(item="a", importance=1.0, status="resolved")],
    )
    assert st2.confidence == pytest_approx(1.0)  # 1 - 0.0


def test_confidence_with_hypotheses():
    """03/00 §3.3 仮説あり: confidence = 0.5×(1−unknown_level) + 0.5×mean(hyp)"""
    st = new_state(
        goal="g",
        unknown=[
            UnknownItem(item="a", importance=0.4, status="unresolved"),
            UnknownItem(item="b", importance=0.6, status="resolved"),
        ],
    )
    # unknown_level = (0.4×1 + 0.6×0)/(0.4+0.6) = 0.4
    assert st.unknown_level == pytest_approx(0.4)
    st.hypotheses = [Hypothesis(statement="h1", confidence=0.8)]
    st.refresh_derived()
    # confidence = 0.5×(1−0.4) + 0.5×0.8 = 0.3 + 0.4 = 0.7
    assert st.confidence == pytest_approx(0.7)


def test_abstention_on_confidence_below_floor():
    """棄権条件: confidence < 0.3 → abstain"""
    st = new_state(
        goal="g",
        unknown=[UnknownItem(item="a", importance=1.0, status="unresolved")],
    )
    st.apply_abstention(confidence_lt=0.3, unknown_level_ge=0.7)
    assert st.judgment == "abstain"


def test_abstention_on_unknown_level_high():
    """棄権条件: unknown_level >= 0.7 → abstain"""
    st = new_state(
        goal="g",
        unknown=[
            UnknownItem(item="a", importance=0.9, status="unresolved"),
            UnknownItem(item="b", importance=0.1, status="resolved"),
        ],
    )
    st.apply_abstention(confidence_lt=0.3, unknown_level_ge=0.7)
    assert st.judgment == "abstain"


def test_no_abstention_when_confident():
    st = new_state(
        goal="g",
        unknown=[UnknownItem(item="a", importance=1.0, status="resolved")],
    )
    st.apply_abstention(confidence_lt=0.3, unknown_level_ge=0.7)
    assert st.judgment == "normal"


def test_serialization_round_trip():
    """YAML 直列化 → 復元で同一構造になること。"""
    st = new_state(
        goal="g",
        context="ctx",
        known=["k1"],
        unknown=[UnknownItem(item="u1", importance=0.7, status="unresolved")],
        phase="create",
    )
    st.hypotheses = [Hypothesis(statement="h", confidence=0.6)]
    restored = State.from_yaml(st.to_yaml())
    assert restored.to_dict() == st.to_dict()


def pytest_approx(value):
    return pytest.approx(value)
