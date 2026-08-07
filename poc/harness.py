"""実験ハーネス — 対照実験の実行制御（ブラインド・カウンターバランス・記録）。

正版: docs/11_実装計画とロードマップ/09_最初の動く試作品設計書.md
実験プロトコル（11/09 §13 評価者の独立性）:
    1. ブラインド化   — 評価器には条件ラベルを渡さない（evaluator 側で保証）
    2. 独立評価系統   — 生成と評価で別モデル（claude_client で強制）
    3. カウンターバランス — 条件順・タスク順をシード付きシャッフルで偏り回避

永続化:
    - memory/trials/*.yaml   … ブラインド試行記録（条件ラベルなし・証拠ファイル）
    - experiments/LOG.yaml   … 条件→trace_id の対応表（解析用。証拠ファイルとは分離）
"""

from __future__ import annotations

import random
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

import yaml

from core.orchestrator import Orchestrator
from memory.store import MemoryStore, TrialRecord
from poc.conditions import MAX_EXPLORE_ITERATIONS, ConditionResult, run_condition
from poc.tasks import POCTask


class Generator(Protocol):
    def generate(self, system: str, user: str) -> str: ...


class Evaluator(Protocol):
    def evaluate(self, system: str, user: str) -> str: ...


@dataclass
class ExperimentLogEntry:
    """実験ログの1試行（条件ラベル付き・解析用）。証拠ファイル（trials/）とは分離する。"""

    trace_id: str
    condition: str
    task_id: str
    decision: str
    success: bool
    abstained: bool
    confidence: float
    unknown_level: float
    overall: float | None
    error: str | None = None


@dataclass
class ExperimentRun:
    """1回の実験実行の結果。"""

    entries: list[ExperimentLogEntry] = field(default_factory=list)
    run_id: str = field(default_factory=lambda: f"run-{uuid.uuid4().hex[:8]}")

    def for_condition(self, condition: str) -> list[ExperimentLogEntry]:
        return [e for e in self.entries if e.condition == condition]

    def successes(self, condition: str) -> int:
        return sum(1 for e in self.for_condition(condition) if e.success)

    def trials(self, condition: str) -> int:
        return len(self.for_condition(condition))


class Harness:
    """条件×タスクの試行を逐次実行する。ブラインド評価は各条件の責任で行う。"""

    def __init__(
        self,
        *,
        generator: Generator,
        evaluator: Evaluator,
        orchestrator: Orchestrator,
        store: MemoryStore,
        experiment_dir: str | Path,
        pass_threshold: float,
        seed: int = 42,
        max_explore_iterations: int = MAX_EXPLORE_ITERATIONS,
    ):
        self.generator = generator
        self.evaluator = evaluator
        self.orchestrator = orchestrator
        self.store = store
        self.experiment_dir = Path(experiment_dir)
        self.experiment_dir.mkdir(parents=True, exist_ok=True)
        self.pass_threshold = pass_threshold
        self.max_explore_iterations = max_explore_iterations
        self.rng = random.Random(seed)

    def _run_one(self, condition: str, task: POCTask) -> ConditionResult:
        """1試行を実行する。例外は「崩れた出力」として明示的失敗に変換し、実験全体は継続。

        生成系が空応答等で例外を投げても、1試行の失敗で実験全体を中断しない
        （wisdom-council-layer 方針: サイレントドロップ禁止・明示的な失敗記録）。
        崩れた出力は手で直さず、error 付きの失敗結果として記録する。
        """
        try:
            return run_condition(
                condition,
                self.generator,
                self.evaluator,
                self.orchestrator,
                self.store,
                task_id=task.id,
                task_prompt=task.prompt,
                pass_threshold=self.pass_threshold,
                max_explore_iterations=self.max_explore_iterations,
            )
        except Exception as e:  # noqa: BLE001 — 任意の崩れを明示的失敗に変換する
            return ConditionResult(
                condition=condition,
                task_id=task.id,
                task_prompt=task.prompt,
                artifact="",
                evaluation=None,
                success=False,
                abstained=False,
                decision="error",
                confidence=0.0,
                unknown_level=0.0,
                reason=f"試行中に例外: {e}",
                error=str(e),
            )

    def run(
        self,
        conditions: list[str],
        tasks: list[POCTask],
        *,
        n_reps: int = 1,
    ) -> ExperimentRun:
        """カウンターバランス付きで条件×タスクを n_reps 回実行する。

        シャッフルにより、実行時刻・タスクの影響が条件間に偏らないようにする。
        （条件順シャッフル → タスク順シャッフル を各リピートで行う）
        """
        run = ExperimentRun()
        for rep in range(n_reps):
            cond_order = list(conditions)
            self.rng.shuffle(cond_order)
            for condition in cond_order:
                task_order = list(tasks)
                self.rng.shuffle(task_order)
                for task in task_order:
                    result = self._run_one(condition, task)
                    entry = self._to_entry(result)
                    run.entries.append(entry)
                    # 証拠ファイル（ブラインド）と解析用ログを逐次保存
                    self._save_trial(result, entry)
                    self._save_log(run)
        return run

    def _to_entry(self, r: ConditionResult) -> ExperimentLogEntry:
        return ExperimentLogEntry(
            trace_id=r.trace_id or f"trial-{uuid.uuid4().hex[:8]}",
            condition=r.condition,
            task_id=r.task_id,
            decision=r.decision,
            success=r.success,
            abstained=r.abstained,
            confidence=r.confidence,
            unknown_level=r.unknown_level,
            overall=r.evaluation.overall if r.evaluation else None,
            error=r.error,
        )

    def _save_trial(self, r: ConditionResult, entry: ExperimentLogEntry) -> None:
        """ブラインド証拠ファイル（条件ラベルなし）を保存する。"""
        if r.evaluation is None:
            # 生成失敗時はブラインド試行記録を作れない（成果物がない）
            return
        record = TrialRecord(
            trace_id=entry.trace_id,
            task_id=r.task_id,
            task_prompt=r.task_prompt,
            artifact=r.artifact,
            evaluation={
                "scores": r.evaluation.scores,
                "overall": r.evaluation.overall,
                "judgment": r.evaluation.passed,
            },
            success=r.success,
            abstained=r.abstained,
            confidence=r.confidence,
            unknown_level=r.unknown_level,
            reason=r.reason,
        )
        self.store.save_trial(record)

    def _save_log(self, run: ExperimentRun) -> None:
        """解析用ログ（条件ラベル付き）を保存する。"""
        path = self.experiment_dir / "experiment_log.yaml"
        data = {
            "run_id": run.run_id,
            "pass_threshold": self.pass_threshold,
            "n_entries": len(run.entries),
            "entries": [asdict(e) for e in run.entries],
        }
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def load_experiment_log(path: str | Path) -> list[ExperimentLogEntry]:
    """保存済みの実験ログを読み込む（レポート・統計用）。"""
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [ExperimentLogEntry(**e) for e in data["entries"]]
