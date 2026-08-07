"""条件実行モジュール — B0（単純指示）と C4（Insight Synapse 全成分）。

正版: docs/11_実装計画とロードマップ/09_最初の動く試作品設計書.md
（C1〜C3 の要因実験は含まない。Step 1 は B0 vs C4 の対照のみ先行実装）

データフロー（1試行・C4）:
    Task Prompt
      → known/unknown 列挙（生成系Claude）→ State 構築
      → Orchestrator.decide(state) → abstain / explore / create
      → Analysis Skill（生成系Claude）→ 成果物
      → 評価（独立評価系統Claude・ブラインド）→ 5軸スコア + overall
      → State 更新 + Memory 保存（Thought Trace / Decision / Trial）
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Protocol

from core.orchestrator import Orchestrator
from core.state import State, UnknownItem, new_state
from evaluation.evaluator import EvaluationResult
from memory.store import MemoryStore, ThoughtTrace

# 分析スキル: Target / Value / Risk / Opportunity（11/09 §5）
ANALYSIS_SYSTEM = (
    "あなたはAIサービス企画の専門家です。与えられたテーマを"
    "Target（対象顧客）・Value（提供価値）・Risk（リスク）・Opportunity（機会）の"
    "4観点で分析してください。分析は具体的・整合的・実行可能であること。"
)

# 既知/未知の列挙を促すプロンプト（C4 のみ使用）
# JSON必須: 実モデルは長い説明文を返しがちなため、出力形式を最優先で固定する
UNKNOWN_ENUMERATION_SYSTEM = (
    "あなたはAIサービス企画の専門家です。このテーマについて"
    "「既に分かっていること（known）」と「分かっていない・不確実なこと（unknown）」を"
    "JSONオブジェクトだけで整理してください。"
    "Markdown・説明文・前置き・コードブロックは一切書かないこと。"
)

# 再生成リトライ（wisdom-council-layer 方式: 崩れたら再生成）最大試行回数
MAX_ENUMERATION_RETRIES = 3  # 評価スコアのリトライ回数は evaluation/evaluator.py が所有

# 探索（unknown_level >= 0.6）時の付加指示: 未知を明示的に扱う
EXPLORE_GUIDANCE = (
    "\n\n【重要な方針】あなたはこのテーマについてまだ十分な情報を持っていません。"
    "自信のない点を推測で埋めず、次のことを行ってください:\n"
    "1. 何が分かっていないかを明示する\n"
    "2. 不確実な前提を明示する\n"
    "3. それでも判断できる部分についてだけ、暫定的な分析を示す\n"
    "4. どの情報を集めれば結論に近づくかを示す"
)

# 棄権（confidence < 0.3 または unknown_level >= 0.7）時の付加指示: 判断保留
ABSTAIN_GUIDANCE = (
    "\n\n【重要な方針】あなたはこのテーマについて十分な情報を持たず、"
    "自信のある結論を出せる状態ではありません。無理に断定せず、次のことを行ってください:\n"
    "1. なぜ結論を出せないか（不明点）を正直に列挙する\n"
    "2. 判断を保留したまま、どの情報を集めれば判断できるかを示す\n"
    "3. 代替案を列挙し、それぞれの不確実性を評価する\n"
    "4. 断定表現（「〜である」「確実に」）を避ける"
)


@dataclass
class ConditionResult:
    """1試行の実行結果。条件ラベルは**内部管理のみ**（評価はブラインド）。

    評価器には artifact と task_prompt だけを渡し、condition は渡さない。
    """

    condition: str                 # "B0" / "C4"（内部管理）
    task_id: str
    task_prompt: str
    artifact: str
    evaluation: EvaluationResult | None
    success: bool                  # overall >= pass_threshold
    abstained: bool
    decision: str                  # "direct"(B0) / "abstain" / "explore" / "create"(C4)
    confidence: float
    unknown_level: float
    reason: str = ""
    trace_id: str | None = None
    error: str | None = None


class Generator(Protocol):
    """生成系Claude（Skill発行）のインターフェイス。"""

    def generate(self, system: str, user: str) -> str: ...


class Evaluator(Protocol):
    """独立評価系統Claudeのインターフェイス（評価は別系統）。"""

    def evaluate(self, system: str, user: str) -> str: ...


# ---------------- B0: 単純な指示、Memoryなし ----------------

def run_b0(
    generator: Generator,
    evaluator: Evaluator,
    *,
    task_id: str,
    task_prompt: str,
    pass_threshold: float,
) -> ConditionResult:
    """B0: タスクプロンプトをそのまま生成系に渡し、成果物をブラインド評価する。

    State / Orchestrator / Memory / 棄権機構 は一切使わない。
    """
    artifact = generator.generate(system=ANALYSIS_SYSTEM, user=task_prompt)
    from evaluation.evaluator import EvaluationEngine

    engine = EvaluationEngine(evaluator, pass_threshold=pass_threshold)
    result = engine.evaluate(artifact, task_prompt)
    return ConditionResult(
        condition="B0",
        task_id=task_id,
        task_prompt=task_prompt,
        artifact=artifact,
        evaluation=result,
        success=result.passed,
        abstained=False,
        decision="direct",
        confidence=0.0,     # B0 は State を持たない（該当なし）
        unknown_level=0.0,
        reason="単純指示: State/Memory/Orchestrator なしで直接生成",
    )


# ---------------- C4: Insight Synapse 全成分 ----------------

def _first_json_object(text: str) -> str | None:
    """テキスト中から最初の平衡した JSON オブジェクト {...} を抽出する。

    前後に Markdown・説明文があっても動作する（文字列内の { } は無視）。
    """
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def parse_known_unknown(text: str) -> tuple[list[str], list[UnknownItem]]:
    """生成系Claude の既知/未知応答をパースする。

    壊れた出力は手で直さず「再生成」対象にするため、parse に失敗したら
    明確な ValueError を投げる（broken output → regenerate 方針）。
    まず全文を JSON として試し、次に平衡ブラケット抽出で `known` を含む
    オブジェクトを探す。
    """
    candidates: list[str] = []
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        candidates.append(stripped)  # 応答全体がJSON
    obj = _first_json_object(text)
    if obj and obj not in candidates:
        candidates.append(obj)

    for cand in candidates:
        try:
            data = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict) or "known" not in data:
            continue
        known = [str(k) for k in data.get("known", [])]
        unknown = []
        for u in data.get("unknown", []):
            if not isinstance(u, dict):
                continue
            status = str(u.get("status", "unresolved"))
            if status not in ("resolved", "partial", "unresolved"):
                status = "unresolved"
            unknown.append(
                UnknownItem(
                    item=str(u.get("item", "")),
                    importance=_clamp(float(u.get("importance", 0.5))),
                    status=status,
                )
            )
        if unknown:
            return known, unknown
    raise ValueError(f"known/unknown 応答をパースできませんでした（再生成対象）: {text[:200]}")


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def _enumerate_known_unknown(generator: Generator, task_prompt: str) -> tuple[list[str], list[UnknownItem]]:
    """既知/未知を列挙させ、形式エラー時はエラー内容をフィードバックして再生成する（最大3回）。

    wisdom-council-layer 方式: 崩れた出力は手で直さず再生成する。
    """
    base_user = (
        f"テーマ：{task_prompt}\n\n"
        "known は既に分かっていること、unknown は分かっていない・不確実なこと。"
        "unknown の各項目に重要度（0.0〜1.0）と解決度（resolved / partial / unresolved）を付けること。\n"
        '出力はこの形式のJSONオブジェクトのみ:\n'
        '{"known": ["..."], "unknown": [{"item": "...", "importance": 0.5, "status": "unresolved"}]}'
    )
    last_err = ""
    for attempt in range(MAX_ENUMERATION_RETRIES):
        feedback = ""
        if attempt > 0:
            feedback = (
                "\n\n前回の出力は形式エラーでした: "
                f"{last_err}\n説明文を一切付けず、JSONオブジェクトのみを出力してください。"
            )
        raw = generator.generate(system=UNKNOWN_ENUMERATION_SYSTEM, user=base_user + feedback)
        try:
            return parse_known_unknown(raw)
        except ValueError as e:
            last_err = str(e)
    raise ValueError(
        f"known/unknown列挙が{MAX_ENUMERATION_RETRIES}回連続で形式エラー（再生成済み）: {last_err}"
    )


def build_thought_trace(
    *,
    state_before: State,
    decision: str,
    reason: str,
    state_after: State,
) -> ThoughtTrace:
    """State遷移から Thought Trace を組み立てる（05/01 のYAML Schema に対応）。"""
    return ThoughtTrace(
        state_before={
            "goal": state_before.goal,
            "unknown": [u.item for u in state_before.unknown],
            "unknown_level": state_before.unknown_level,
            "confidence": state_before.confidence,
        },
        observation=[state_before.active_question or state_before.goal],
        hypothesis=[h.statement for h in state_before.hypotheses],
        decision=decision,
        reason=reason,
        rejected_alternatives=[],
        state_after={
            "phase": state_after.phase,
            "unknown_level": state_after.unknown_level,
            "confidence": state_after.confidence,
        },
        confidence_delta=f"{state_after.confidence - state_before.confidence:+.2f}",
    )


def run_c4(
    generator: Generator,
    evaluator: Evaluator,
    orchestrator: Orchestrator,
    store: MemoryStore,
    *,
    task_id: str,
    task_prompt: str,
    pass_threshold: float,
) -> ConditionResult:
    """C4: unknown 明示管理 + Thought Trace + Orchestrator 制御の全サイクル。

    1. 生成系Claudeに既知/未知を列挙させ、State を構築
    2. Orchestrator が次のActionを決定（abstain / explore / create）
    3. Actionに応じた方針指示を付けて Analysis Skill で成果物生成
    4. ブラインド評価（独立評価系統）
    5. State更新 + Thought Trace / Decision / Trial を保存
    """
    from evaluation.evaluator import EvaluationEngine

    engine = EvaluationEngine(evaluator, pass_threshold=pass_threshold)

    # ---- 1. 既知/未知の列挙 → State 構築（形式エラー時は再生成リトライ） ----
    try:
        known, unknown = _enumerate_known_unknown(generator, task_prompt)
    except Exception as e:  # 3回再生成後も失敗 → broken output として明示的に失敗記録
        return ConditionResult(
            condition="C4",
            task_id=task_id,
            task_prompt=task_prompt,
            artifact="",
            evaluation=None,
            success=False,
            abstained=False,
            decision="error",
            confidence=0.0,
            unknown_level=0.0,
            reason=f"known/unknown列挙に失敗: {e}",
            error=str(e),
        )

    state = new_state(
        goal=task_prompt,
        context="AIサービス企画分析タスク",
        phase="understand",
        known=known,
        unknown=unknown,
    )

    # ---- 2. Orchestrator が次のActionを決定 ----
    decision = orchestrator.decide(state)
    state.phase = "explore" if decision.action != "create" else "design"
    state.active_question = task_prompt
    state.refresh_derived()

    # ---- 3. Actionに応じた方針で Analysis Skill 実行 ----
    guidance = ""
    if decision.action == "abstain":
        guidance = ABSTAIN_GUIDANCE
    elif decision.action == "explore":
        guidance = EXPLORE_GUIDANCE

    artifact = generator.generate(system=ANALYSIS_SYSTEM + guidance, user=task_prompt)

    # ---- 4. ブラインド評価（条件情報を一切渡さない） ----
    result = engine.evaluate(artifact, task_prompt)

    # ---- 5. State 更新 + Memory 保存 ----
    # state_before は「分析前の認知状態」のスナップショット（deepcopy）を取る
    state_before = deepcopy(state)
    state.phase = "evaluate"
    state.known.append(f"評価: overall={result.overall:.2f}")
    state.refresh_derived()

    trace = build_thought_trace(
        state_before=state_before,
        decision=decision.action,
        reason=decision.reason,
        state_after=state,
    )
    trace_id = store.save_trace(trace)
    store.save_decision(
        {
            "condition": "C4",
            "task_id": task_id,
            "action": decision.action,
            "reason": decision.reason,
            "confidence": state.confidence,
            "unknown_level": state.unknown_level,
            "judgment": state.judgment,
        }
    )

    return ConditionResult(
        condition="C4",
        task_id=task_id,
        task_prompt=task_prompt,
        artifact=artifact,
        evaluation=result,
        success=result.passed,
        abstained=(state.judgment == "abstain"),
        decision=decision.action,
        confidence=state.confidence,
        unknown_level=state.unknown_level,
        reason=decision.reason,
        trace_id=trace_id,
    )


# 実行関数のディスパッチ
RUNNERS = {
    "B0": run_b0,
    "C4": run_c4,
}


def run_condition(
    condition: str,
    generator: Generator,
    evaluator: Evaluator,
    orchestrator: Orchestrator,
    store: MemoryStore,
    *,
    task_id: str,
    task_prompt: str,
    pass_threshold: float,
) -> ConditionResult:
    """条件名で実行関数を選ぶ。B0 は C4 用の引数（orchestrator/store）を無視する。"""
    if condition == "B0":
        return run_b0(
            generator, evaluator, task_id=task_id, task_prompt=task_prompt,
            pass_threshold=pass_threshold,
        )
    if condition == "C4":
        return run_c4(
            generator, evaluator, orchestrator, store,
            task_id=task_id, task_prompt=task_prompt, pass_threshold=pass_threshold,
        )
    raise ValueError(f"未実装の条件: {condition!r}（実装済み: B0, C4）")
