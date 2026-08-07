"""実験レポート生成のテスト（2026-08-08 追加）。

対象: poc/report.py の build_report。
C4 単独実行で best_baseline が ValueError を投げてクラッシュした（2026-08-08 dev検証）のを
受けて、単一条件・C4 を含まない実行では効果量計算をスキップする修正を検証する。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from poc.config import POCConfig  # noqa: E402
from poc.harness import ExperimentLogEntry, ExperimentRun  # noqa: E402
from poc.report import build_report  # noqa: E402


def _entry(cond: str, task: str, success: bool, overall: float) -> ExperimentLogEntry:
    return ExperimentLogEntry(
        trace_id=f"trial-{cond}-{task}",
        condition=cond,
        task_id=task,
        decision="direct",
        success=success,
        abstained=False,
        confidence=0.5,
        unknown_level=0.5,
        overall=overall,
    )


def _cfg() -> POCConfig:
    return POCConfig.load()


def test_build_report_single_condition_c4_no_crash():
    """C4 単独実行では効果量計算をスキップし、クラッシュせずレポートを返す。"""
    cfg = _cfg()
    run = ExperimentRun()
    run.entries.append(_entry("C4", "prod-01", False, 0.67))

    report = build_report(cfg, run, conditions=("C4",), task_set="prod")

    assert "効果量は**計算不可**" in report
    assert "| C4 | 0/1 | 0.0%" in report


def test_build_report_multi_condition_has_effect():
    """複数条件（B0, C4）では効果量セクションが正しく生成される（既存動作の回帰）。"""
    cfg = _cfg()
    run = ExperimentRun()
    run.entries.append(_entry("B0", "prod-01", True, 0.80))
    run.entries.append(_entry("C4", "prod-01", True, 0.85))

    report = build_report(cfg, run, conditions=("B0", "C4"), task_set="prod")

    assert "最良ベースライン" in report
    assert "効果量" in report
    assert "判定帯域" in report
    assert "計算不可" not in report
