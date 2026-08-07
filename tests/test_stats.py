"""実験統計の単体テスト。

検証対象: docs/03_コアコンポーネント/00_数値定義書.md §8（効果量・判定帯域・追試ルール）
"""

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from poc.stats import (
    best_baseline,
    difference_ci,
    judge,
    judge_after_followup,
    summarize_condition,
    wilson_ci,
)


@dataclass
class _Entry:
    success: bool


def test_wilson_ci_perfect():
    """20/20 → rate=1.0、下限は0.83より大きい。"""
    ci = wilson_ci(20, 20)
    assert ci.rate == pytest.approx(1.0)
    assert ci.low > 0.83
    assert ci.high == pytest.approx(1.0)


def test_wilson_ci_zero():
    """0/20 → rate=0.0、上限は0.17より小さい。"""
    ci = wilson_ci(0, 20)
    assert ci.rate == pytest.approx(0.0)
    assert ci.high < 0.17
    assert ci.low == pytest.approx(0.0)


def test_wilson_ci_midpoint_symmetric():
    """10/20 → 50%、CIは0.5を挟む。"""
    ci = wilson_ci(10, 20)
    assert ci.rate == pytest.approx(0.5)
    assert ci.low < 0.5 < ci.high


def test_wilson_ci_zero_n():
    ci = wilson_ci(0, 0)
    assert ci.n == 0
    assert ci.rate == 0.0


def test_judge_bands():
    """判定帯域（03/00 §8.1）: <5 reject / 5-20 indeterminate / 20-39 uncertain / >=39 support。"""
    assert judge(4.9) == "reject"
    assert judge(5.0) == "indeterminate"
    assert judge(19.9) == "indeterminate"
    assert judge(20.0) == "uncertain"
    assert judge(38.9) == "uncertain"
    assert judge(39.0) == "support"
    assert judge(60.0) == "support"


def test_judge_negative_is_reject():
    assert judge(-10.0) == "reject"


def test_judge_after_followup():
    """追試後（03/00 §8.3）: <5 reject / >=20 support / 中間は indeterminate。"""
    assert judge_after_followup(4.0) == "reject"
    assert judge_after_followup(20.0) == "support"
    assert judge_after_followup(12.0) == "indeterminate"


def test_difference_ci_value():
    """C4 15/20 (75%) vs B0 10/20 (50%) → diff=25pp → uncertain。"""
    d = difference_ci(s1=15, n1=20, s2=10, n2=20)
    assert d.diff_pp == pytest.approx(25.0)
    assert d.judgment == "uncertain"
    assert d.followup_verdict == "support"  # 追試相当では >=20pp → support
    assert d.low_pp < d.diff_pp < d.high_pp


def test_difference_ci_large_effect_support():
    """C4 18/20 (90%) vs B0 8/20 (40%) → diff=50pp → support。"""
    d = difference_ci(s1=18, n1=20, s2=8, n2=20)
    assert d.diff_pp == pytest.approx(50.0)
    assert d.judgment == "support"


def test_difference_ci_small_effect_reject():
    """C4 11/20 (55%) vs B0 10/20 (50%) → diff=5pp → indeterminate 境界。"""
    d = difference_ci(s1=11, n1=20, s2=10, n2=20)
    assert d.diff_pp == pytest.approx(5.0)
    assert d.judgment == "indeterminate"


def test_summarize_condition():
    entries = [_Entry(True), _Entry(True), _Entry(False), _Entry(True)]
    s = summarize_condition(entries)
    assert s["n"] == 4
    assert s["successes"] == 3
    assert s["success_rate"] == pytest.approx(0.75)
    assert s["ci_low"] < 0.75 < s["ci_high"]


def test_best_baseline_excludes_c4():
    rates = {"B0": 0.4, "B1": 0.5, "B2": 0.45, "C4": 0.9}
    assert best_baseline(rates) == "B1"


def test_best_baseline_raises_when_no_baseline():
    with pytest.raises(ValueError):
        best_baseline({"C4": 0.9})
