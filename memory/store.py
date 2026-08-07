"""Memory System — 思考資産のファイルシステム永続化。

正版: docs/05_メモリー/01_メモリーアーキテクチャ仕様書.md
Thought Trace（YAML）/ Decision Log（Markdown）/ Pattern（Markdown）を保存する。

原則: 「何を知っていたか」ではなく「どう考えたか」を保存する。
書き込みは連続ではなく、重要なイベント（判断変更・失敗・成功・新パターン）でのみ行う。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml


@dataclass
class ThoughtTrace:
    """Thought Trace — 1ユニットの認知遷移。05/01 のYAML Schema に対応。

    構造: state_before → observation → hypothesis → decision
          → reason + rejected_alternatives → state_after → confidence_delta
    """

    id: str = field(default_factory=lambda: f"trace-{uuid.uuid4().hex[:8]}")
    timestamp: str = field(default_factory=lambda: _now_iso())
    state_before: dict = field(default_factory=dict)  # goal, unknown, confidence
    observation: list[str] = field(default_factory=list)
    hypothesis: list[str] = field(default_factory=list)
    decision: str = ""
    reason: str = ""
    rejected_alternatives: list[str] = field(default_factory=list)
    state_after: dict = field(default_factory=dict)  # phase, confidence
    confidence_delta: str = ""


@dataclass
class TrialRecord:
    """1試行の記録（実験ハーネスが保存する）。盲検化のため条件ラベルは持たない。"""

    trace_id: str
    task_id: str
    task_prompt: str
    artifact: str
    evaluation: dict  # 5軸スコア + overall
    success: bool
    abstained: bool
    confidence: float
    unknown_level: float
    reason: str = ""


class MemoryStore:
    """traces / decisions / patterns を YAML または Markdown で保存する。"""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.traces_dir = self.root / "traces"
        self.decisions_dir = self.root / "decisions"
        self.patterns_dir = self.root / "patterns"
        for d in (self.traces_dir, self.decisions_dir, self.patterns_dir):
            d.mkdir(parents=True, exist_ok=True)

    # ---- Thought Trace ----

    def save_trace(self, trace: ThoughtTrace) -> str:
        """Thought Trace を YAML として保存し、trace_id を返す。"""
        path = self.traces_dir / f"{trace.id}.yaml"
        path.write_text(yaml.safe_dump(trace.__dict__, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return trace.id

    def load_trace(self, trace_id: str) -> ThoughtTrace:
        path = self.traces_dir / f"{trace_id}.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return ThoughtTrace(**data)

    # ---- Decision Log ----

    def save_decision(self, decision: dict) -> str:
        """Decision Log を Markdown として保存し、decision_id を返す。"""
        did = f"decision-{uuid.uuid4().hex[:8]}"
        lines = [
            "# Decision Record",
            f"- **id**: {did}",
            f"- **timestamp**: {_now_iso()}",
            "",
        ]
        for k, v in decision.items():
            lines.append(f"## {k}")
            lines.append(str(v))
            lines.append("")
        path = self.decisions_dir / f"{did}.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return did

    # ---- Pattern ----

    def save_pattern(self, pattern: dict) -> str:
        """成功・失敗パターンを Markdown として保存し、pattern_id を返す。"""
        pid = f"pattern-{uuid.uuid4().hex[:8]}"
        lines = [
            "# Pattern",
            f"- **id**: {pid}",
            f"- **timestamp**: {_now_iso()}",
            "",
        ]
        for k, v in pattern.items():
            lines.append(f"## {k}")
            lines.append(str(v))
            lines.append("")
        path = self.patterns_dir / f"{pid}.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return pid

    # ---- 実験記録（ブラインド） ----

    def save_trial(self, record: TrialRecord) -> str:
        """試行記録を YAML として保存。条件ラベルは含めない（ブラインド化）。"""
        path = self.root / "trials" / f"{record.trace_id}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(record.__dict__, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return record.trace_id

    def list_traces(self) -> list[str]:
        return sorted(p.stem for p in self.traces_dir.glob("*.yaml"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
