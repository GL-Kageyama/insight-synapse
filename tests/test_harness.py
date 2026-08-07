"""ハーネスの例外処理テスト（2026-08-08 追加）。

対象: poc/harness.py の _run_one が生成系の例外（空応答等）を
明示的失敗に変換し、実験全体を中断しないこと。
dev 検証で空応答の RuntimeException が試行全体を止めたことを受けて追加。
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.orchestrator import Orchestrator  # noqa: E402
from memory.store import MemoryStore  # noqa: E402
from poc.conditions import ConditionResult, run_condition  # noqa: E402
from poc.harness import Harness  # noqa: E402
from poc.tasks import POCTask  # noqa: E402


class ExplodingGenerator:
    """生成系が常に例外を投げるモック（空応答の再生成失敗を模す）。"""

    def generate(self, system: str, user: str) -> str:
        raise RuntimeError("空の応答（モデルが空文字列を返した）")

    def evaluate(self, system: str, user: str) -> str:
        return '{"quality": 0.8, "logic": 0.8, "creativity": 0.8, "value": 0.8, "risk": 0.2}'


class DummyEvaluator:
    def evaluate(self, system: str, user: str) -> str:
        return '{"quality": 0.8, "logic": 0.8, "creativity": 0.8, "value": 0.8, "risk": 0.2}'


def _task(tid: str) -> POCTask:
    return POCTask(id=tid, theme="AIサービスの企画", prompt="AIサービスの企画")


def _make_harness(store, generator=None, evaluator=None):
    return Harness(
        generator=generator or ExplodingGenerator(),
        evaluator=evaluator or DummyEvaluator(),
        orchestrator=Orchestrator(),
        store=store,
        experiment_dir=store.root,
        pass_threshold=0.70,
        seed=42,
    )


def test_run_one_converts_exception_to_explicit_failure(tmp_path):
    """生成系の例外は明示的失敗（decision=error）に変換され、例外を投げない。"""
    store = MemoryStore(tmp_path)
    harness = _make_harness(store)
    result = harness._run_one("B0", _task("t1"))
    assert isinstance(result, ConditionResult)
    assert result.success is False
    assert result.decision == "error"
    assert result.error is not None
    assert "空の応答" in result.error


def test_run_continues_after_exception(tmp_path):
    """1試行が失敗しても run() は中断せず、全試行を実行して記録する。"""
    store = MemoryStore(tmp_path)
    harness = _make_harness(store)
    run = harness.run(["B0"], [_task("t1"), _task("t2")], n_reps=1)
    assert len(run.entries) == 2
    for entry in run.entries:
        assert entry.condition == "B0"
        assert entry.decision == "error"
        assert entry.success is False
        assert entry.error is not None


def test_run_one_success_path_passes_through(tmp_path):
    """正常な生成は例外変換されず、そのまま成功結果が返る。"""

    class GoodGenerator:
        def generate(self, system: str, user: str) -> str:
            return "正常な成果物"

    store = MemoryStore(tmp_path)
    harness = _make_harness(store, generator=GoodGenerator())
    result = harness._run_one("B0", _task("t3"))
    assert result.success is True
    assert result.decision == "direct"
