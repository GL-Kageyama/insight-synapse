"""POCConfig（思考品質レベル）のテスト（2026-08-08 追加）。

検証対象: docs/03_コアコンポーネント/00_数値定義書.md §3.4 追記の思考品質レベル
（L1 エコノミー / L2 スタンダード / L3 ディープ）と、各レベルに対応する探索反復上限。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from poc.config import POCConfig  # noqa: E402


def _cfg(quality: int) -> POCConfig:
    return POCConfig(
        params={
            "thinking_quality": quality,
            "quality_levels": {
                "L1": {"name": "エコノミー", "explore_iterations": 1},
                "L2": {"name": "スタンダード", "explore_iterations": 5},
                "L3": {"name": "ディープ", "explore_iterations": 8},
            },
            # validate に必要な最小要素
            "criteria": {
                "quality": 0.25, "logic": 0.20, "creativity": 0.20, "value": 0.25, "risk": 0.10,
            },
            "thresholds": {"pass": 0.70, "revise": 0.50},
            "decision": {
                "explore_when_unknown_level_ge": 0.6,
                "create_when_confidence_ge": 0.75,
                "create_when_unknown_level_le": 0.25,
            },
            "abstention": {"confidence_lt": 0.15, "unknown_level_ge": 0.85},
            "claude": {
                "generation_model": "claude-sonnet-4-5",
                "evaluation_model": "claude-haiku-4-5",
                "temperature": 0.0,
            },
        }
    )


def test_quality_levels_map_to_explore_iterations():
    """L1/L2/L3 はそれぞれ探索反復 1/5/8 に対応する。"""
    assert _cfg(1).thinking_quality == 1
    assert _cfg(1).explore_iterations == 1  # L1 エコノミー
    assert _cfg(2).explore_iterations == 5  # L2 スタンダード
    assert _cfg(3).explore_iterations == 8  # L3 ディープ


def test_default_quality_is_l2():
    """params に thinking_quality が無い場合は L2（スタンダード=5回）にフォールバックする。"""
    cfg = POCConfig(params={})
    assert cfg.thinking_quality == 2
    assert cfg.explore_iterations == 5


def test_loaded_params_has_quality_default():
    """config/params.yaml の既定は L1（エコノミー）＝開発段階の方針。"""
    cfg = POCConfig.load()
    assert cfg.thinking_quality == 1
    assert cfg.explore_iterations == 1
