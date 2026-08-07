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
    """棄権条件: confidence < 0.15 → abstain（Step 2 較正後）"""
    st = new_state(
        goal="g",
        unknown=[UnknownItem(item="a", importance=1.0, status="unresolved")],
    )
    st.apply_abstention(confidence_lt=0.15, unknown_level_ge=0.85)
    assert st.judgment == "abstain"


def test_abstention_on_unknown_level_high():
    """棄権条件: unknown_level >= 0.85 → abstain（Step 2 較正後）"""
    st = new_state(
        goal="g",
        unknown=[
            UnknownItem(item="a", importance=0.9, status="unresolved"),
            UnknownItem(item="b", importance=0.1, status="resolved"),
        ],
    )
    st.apply_abstention(confidence_lt=0.15, unknown_level_ge=0.85)
    assert st.judgment == "abstain"


def test_no_abstention_when_confident():
    st = new_state(
        goal="g",
        unknown=[UnknownItem(item="a", importance=1.0, status="resolved")],
    )
    st.apply_abstention(confidence_lt=0.15, unknown_level_ge=0.85)
    assert st.judgment == "normal"


def test_abstention_default_recalibrated():
    """デフォルト閾値が params.yaml と整合（0.15 / 0.85）している。

    旧閾値（0.3 / 0.7）では 0.8 で abstain になったが、較正後はしない。
    """
    st = new_state(
        goal="g",
        unknown=[
            UnknownItem(item="a", importance=0.8, status="unresolved"),
            UnknownItem(item="b", importance=0.2, status="resolved"),
        ],
    )
    # unknown_level = 0.8, confidence = 0.2 → デフォルトでは abstain しない
    st.apply_abstention()
    assert st.judgment == "normal"
    # 明示的に旧閾値で呼ぶと abstain になる（較正の意味をテスト）
    st2 = new_state(
        goal="g",
        unknown=[
            UnknownItem(item="a", importance=0.8, status="unresolved"),
            UnknownItem(item="b", importance=0.2, status="resolved"),
        ],
    )
    st2.apply_abstention(confidence_lt=0.3, unknown_level_ge=0.7)
    assert st2.judgment == "abstain"


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


# ---- 探索ループの State 反映（Step 2 で追加）----

def test_resolve_unknown_moves_to_known():
    """resolve_unknown(resolved) は unknown_level を下げる。

    03/00 §3.2: unknown_level = Σ(importance×unresolved) / Σ(importance)。
    resolved は分子に 0、分母には重要度として残るため、
    remove せず status="resolved" に更新する。
    """
    st = new_state(
        goal="g",
        known=["k0"],
        unknown=[
            UnknownItem(item="u1", importance=0.8, status="unresolved"),
            UnknownItem(item="u2", importance=0.2, status="unresolved"),
        ],
    )
    assert st.unknown_level == pytest_approx(1.0)
    st.resolve_unknown("u1", "resolved")
    # 分子 = 0.2×1.0、分母 = 0.8+0.2 → 0.2
    assert st.unknown_level == pytest_approx(0.2)
    # 項目は unknown に残るが status が resolved になっている
    u1 = next(u for u in st.unknown if u.item == "u1")
    assert u1.status == "resolved"


def test_resolve_unknown_partial_reduces_level():
    """partial は unresolved_degree 0.5 として unknown_level に反映。"""
    st = new_state(
        goal="g",
        unknown=[UnknownItem(item="u1", importance=1.0, status="unresolved")],
    )
    assert st.unknown_level == pytest_approx(1.0)
    st.resolve_unknown("u1", "partial")
    assert st.unknown_level == pytest_approx(0.5)


def test_resolve_unknown_unknown_item_noop():
    """存在しない item は何も変えない（該当なし）。"""
    st = new_state(
        goal="g",
        unknown=[UnknownItem(item="u1", importance=1.0, status="unresolved")],
    )
    st.resolve_unknown("存在しない項目", "resolved")
    assert st.unknown_level == pytest_approx(1.0)
    assert len(st.unknown) == 1


def test_add_known_dedup():
    """add_known は重複を追加しない。"""
    st = new_state(goal="g", known=["k1"])
    st.add_known("k1")
    st.add_known("k2")
    assert st.known == ["k1", "k2"]


def test_add_hypothesis_raises_confidence():
    """add_hypothesis は hypotheses に追加し confidence 計算を改善する。"""
    st = new_state(
        goal="g",
        unknown=[UnknownItem(item="u1", importance=1.0, status="unresolved")],
    )
    assert st.confidence == pytest_approx(0.0)
    st.add_hypothesis("h1", confidence=1.0)
    # confidence = 0.5×(1−1.0) + 0.5×1.0 = 0.5
    assert st.confidence == pytest_approx(0.5)


def test_confidence_bounds_clamped():
    """仮説の confidence は 0〜1 にクランプされる。"""
    st = new_state(goal="g")
    st.add_hypothesis("h1", confidence=2.0)
    assert st.hypotheses[0].confidence == pytest_approx(1.0)
    st.add_hypothesis("h2", confidence=-1.0)
    assert st.hypotheses[1].confidence == pytest_approx(0.0)


def pytest_approx(value):
    return pytest.approx(value)
