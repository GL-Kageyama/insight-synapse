"""実験統計 — 成功率・効果量・95%CI・判定帯域。

正版: docs/03_コアコンポーネント/00_数値定義書.md §8（効果量・判定帯域・追試ルール）

効果量の定義（11/09）:
    効果量 = C4成功率 − 最良ベースライン成功率（パーセンテージポイント差）

判定帯域:
    <5pp              → reject（仮説Hを棄却）
    5〜20pp           → indeterminate（追試必須）
    20〜39pp          → uncertain（追試必須）
    >=39pp            → determinative support（決定的事実として支持）

追試ルール: 最大1回、N=74/群。追試後: <5pp → reject、>=20pp → support。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from scipy.stats import norm


@dataclass(frozen=True)
class ProportionCI:
    """成功率と95%Wilson信頼区間。"""

    rate: float
    low: float
    high: float
    successes: int
    n: int


def success_rate(successes: int, n: int) -> float:
    if n <= 0:
        return 0.0
    return successes / n


def wilson_ci(successes: int, n: int, alpha: float = 0.05) -> ProportionCI:
    """Wilsonスコア区間（比率の95%CI。二項比率の信頼区間として推奨）。"""
    if n <= 0:
        return ProportionCI(rate=0.0, low=0.0, high=0.0, successes=0, n=0)
    p = successes / n
    z = norm.ppf(1.0 - alpha / 2.0)
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    half = z * ((p * (1.0 - p) / n + z2 / (4.0 * n * n)) ** 0.5) / denom
    return ProportionCI(
        rate=p,
        low=max(0.0, center - half),
        high=min(1.0, center + half),
        successes=successes,
        n=n,
    )


@dataclass(frozen=True)
class DifferenceResult:
    """2群間の成功率差と95%CI（Newcombeのハイブリッドスコア区間）。"""

    diff_pp: float          # (p1 - p2) × 100、pp単位
    low_pp: float
    high_pp: float
    p1: float
    p2: float
    n1: int
    n2: int
    judgment: str
    followup_verdict: str


def difference_ci(
    s1: int, n1: int, s2: int, n2: int, alpha: float = 0.05
) -> DifferenceResult:
    """成功率差の95%CI（Newcombe法: 両群をWilson区間で補正）。

    diff = p1 − p2。s1/n1 は C4、s2/n2 はベースライン。
    """
    ci1 = wilson_ci(s1, n1, alpha)
    ci2 = wilson_ci(s2, n2, alpha)
    diff = ci1.rate - ci2.rate
    # Newcombe: (p1 - l1)^2 + (u2 - p2)^2 の平方根でロワー幅を、逆でアッパー幅を求める
    low = diff - ((ci1.rate - ci1.low) ** 2 + (ci2.high - ci2.rate) ** 2) ** 0.5
    high = diff + ((ci1.high - ci1.rate) ** 2 + (ci2.rate - ci2.low) ** 2) ** 0.5
    return DifferenceResult(
        diff_pp=diff * 100.0,
        low_pp=low * 100.0,
        high_pp=high * 100.0,
        p1=ci1.rate,
        p2=ci2.rate,
        n1=n1,
        n2=n2,
        judgment=judge(diff * 100.0),
        followup_verdict=judge_after_followup(diff * 100.0),
    )


def judge(diff_pp: float) -> str:
    """判定帯域（03/00 §8.1）: diff_pp = C4成功率 − ベースライン成功率。"""
    if diff_pp < 5.0:
        return "reject"
    if diff_pp < 20.0:
        return "indeterminate"
    if diff_pp < 39.0:
        return "uncertain"
    return "support"


def judge_after_followup(diff_pp: float) -> str:
    """追試後の最終判定（03/00 §8.3）: 最大1回の再現実験で確定。"""
    if diff_pp < 5.0:
        return "reject"
    if diff_pp >= 20.0:
        return "support"
    return "indeterminate"


def summarize_condition(entries: Iterable[object]) -> dict:
    """条件ごとの集計（成功率・CI・試行数）。entry は success / n 属性を持つ想定。"""
    rows = list(entries)
    successes = sum(1 for e in rows if e.success)
    n = len(rows)
    ci = wilson_ci(successes, n)
    return {
        "n": n,
        "successes": successes,
        "success_rate": ci.rate,
        "ci_low": ci.low,
        "ci_high": ci.high,
    }


def best_baseline(success_rates: dict[str, float], *, exclude: str = "C4") -> str:
    """最良ベースライン条件の名前を返す。C4 を除外し、成功率が最大のもの。"""
    candidates = {k: v for k, v in success_rates.items() if k != exclude}
    if not candidates:
        raise ValueError("ベースライン条件がありません")
    return max(candidates, key=candidates.get)
