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

# ---- B1: Reflexion（失敗後に振り返り改善）----
# アルゴリズム: 初期生成 → ブラインド評価 → Pass で終了 / 失敗なら
# 振り返り生成 → 振り返りを踏まえて再生成 → 再評価（計2回生成 + 1回振り返り）
REFLECTION_SYSTEM = (
    "あなたはAIサービス企画の専門家です。前回の分析の弱点を正直に振り返ってください。\n"
    "「なぜ十分でなかったか」「何が足りなかったか」を具体的に言語化し、"
    "次回の分析を改善するための指摘を示してください。\n"
    "自己弁護せず、建設的な批判に徹してください。"
)

# ---- B2: Self-Refine（自己批評 → 改善の反復）----
# アルゴリズム: 初期生成 → 自己批評（同一生成モデル）→ 改善生成 →
# ブラインド評価（評価は常に独立評価系統。自己評価は改善のためだけに使用）
SELF_REFINE_SYSTEM = (
    "あなたはAIサービス企画の専門家です。以下の分析について問題点を指摘してください。\n"
    "曖昧な記述・根拠の薄い主張・欠落している視点・現実性の低い前提などを"
    "具体的に列挙してください。改善のための建設的な指摘に徹してください。"
)

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

# ---- 探索ループ（03/00 §3.4 の Explore 継続 / 11/09 §13）----
# Step 2 で追加: 従来は explore 判定時に付加指示を付けて1回生成するだけだったが、
# unknown を実際に減らす反復探索ループを実装する。

# 1試行の探索反復上限（無限ループ防止）
MAX_EXPLORE_ITERATIONS = 5
# 1反復で扱う unknown の最大件数（重要度の高い順に選択）
EXPLORE_STEP_SIZE = 3

# 探索ステップの指示: 推測で resolved にせず、専門知識から判断できる範囲に限定する
# 重要: resolutions の各項目には、プロンプトで示された項目の番号（index）を必ず付けること。
# 実モデルは item 名を言い換えるため、名前の完全一致に頼らず index で対応付ける（Step 2 修正）。
EXPLORE_STEP_SYSTEM = (
    "あなたはAIサービス企画の専門家です。提示された「分かっていないこと」の各項目について、"
    "専門知識に基づく構造的な分析で解決を試みてください。\n"
    "外部データ（市場調査・ユーザーインタビュー・実測等）の入手が必要で現時点で確定できない項目は、"
    "推測で resolved にせず、partial（部分的に解決）または unresolved（不明のまま）にしてください。\n"
    "「何が分かれば判断できるか」「現時点で確からしい前提」も insight に含めてください。\n"
    '出力はこの形式のJSONオブジェクトのみ:\n'
    '{"resolutions": [{"index": 1, "item": "項目", "status": "resolved|partial|unresolved", '
    '"insight": "この項目について得られた知見"}], '
    '"known": ["新たに分かった事実"], '
    '"hypotheses": [{"statement": "作業仮説", "confidence": 0.7}]}'
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


# ---------------- B1: Reflexion（失敗後に振り返り改善）----------------

def run_b1(
    generator: Generator,
    evaluator: Evaluator,
    *,
    task_id: str,
    task_prompt: str,
    pass_threshold: float,
) -> ConditionResult:
    """B1: 初期生成 → ブラインド評価 → 失敗なら振り返り → 再生成 → 再評価。

    最大1回の振り返り＋再生成（計2回の生成 + 1回の振り返り）。State/Orchestrator は使わない。
    """
    from evaluation.evaluator import EvaluationEngine

    engine = EvaluationEngine(evaluator, pass_threshold=pass_threshold)

    # 1. 初期生成（B0 と同一条件）
    artifact = generator.generate(system=ANALYSIS_SYSTEM, user=task_prompt)
    result = engine.evaluate(artifact, task_prompt)

    if result.passed:
        # 成功 → 振り返りなしで終了
        return ConditionResult(
            condition="B1",
            task_id=task_id,
            task_prompt=task_prompt,
            artifact=artifact,
            evaluation=result,
            success=True,
            abstained=False,
            decision="direct",
            confidence=0.0,
            unknown_level=0.0,
            reason=f"Reflexion: 初期生成が成功（overall={result.overall:.2f}）、振り返り不要",
        )

    # 2. 失敗 → 振り返り生成
    reflection = generator.generate(
        system=REFLECTION_SYSTEM,
        user=(
            f"【元のタスク】\n{task_prompt}\n\n"
            f"【前回の分析（overall={result.overall:.2f}）】\n{artifact}\n\n"
            "この分析が評価で合格しなかった。弱点を振り返り、改善方針を述べよ。"
        ),
    )

    # 3. 振り返りを踏まえて再生成
    artifact2 = generator.generate(
        system=ANALYSIS_SYSTEM,
        user=(
            f"{task_prompt}\n\n"
            f"【前回の振り返り】\n{reflection}\n\n"
            "上記の振り返りを反映し、分析を改善せよ。"
        ),
    )
    result2 = engine.evaluate(artifact2, task_prompt)

    return ConditionResult(
        condition="B1",
        task_id=task_id,
        task_prompt=task_prompt,
        artifact=artifact2,
        evaluation=result2,
        success=result2.passed,
        abstained=False,
        decision="reflexion",
        confidence=0.0,
        unknown_level=0.0,
        reason=f"Reflexion: 初回失敗({result.overall:.2f}) → 振り返り→再生成({result2.overall:.2f})",
    )


# ---------------- B2: Self-Refine（自己批評 → 改善の反復）----------------

def run_b2(
    generator: Generator,
    evaluator: Evaluator,
    *,
    task_id: str,
    task_prompt: str,
    pass_threshold: float,
) -> ConditionResult:
    """B2: 初期生成 → 自己批評 → 改善生成 → ブラインド評価。

    最大1回の自己批評＋改善（計2回の生成 + 1回の批評）。評価は常に独立評価系統。
    """
    from evaluation.evaluator import EvaluationEngine

    engine = EvaluationEngine(evaluator, pass_threshold=pass_threshold)

    # 1. 初期生成（B0 と同一条件）
    artifact = generator.generate(system=ANALYSIS_SYSTEM, user=task_prompt)

    # 2. 自己批評（同一生成モデル。改善のためだけに使用）
    critique = generator.generate(
        system=SELF_REFINE_SYSTEM,
        user=f"【元のタスク】\n{task_prompt}\n\n【分析】\n{artifact}\n\nこの分析の問題点を指摘せよ。",
    )

    # 3. 改善生成
    artifact2 = generator.generate(
        system=ANALYSIS_SYSTEM,
        user=(
            f"{task_prompt}\n\n"
            f"【自己批評】\n{critique}\n\n"
            "上記の指摘を反映し、分析を改善せよ。"
        ),
    )

    # 4. ブラインド評価（独立評価系統）
    result = engine.evaluate(artifact2, task_prompt)

    return ConditionResult(
        condition="B2",
        task_id=task_id,
        task_prompt=task_prompt,
        artifact=artifact2,
        evaluation=result,
        success=result.passed,
        abstained=False,
        decision="self_refine",
        confidence=0.0,
        unknown_level=0.0,
        reason=f"Self-Refine: 初回生成 → 自己批評 → 改善生成（overall={result.overall:.2f}）",
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


def _parse_exploration_result(text: str) -> dict:
    """探索ステップの応答をパースする。

    期待JSON形式:
        {"resolutions": [{"index": 1, "item": ..., "status": "resolved|partial|unresolved",
                          "insight": ...}],
         "known": [...],
         "hypotheses": [{"statement": ..., "confidence": ...}]}
    崩れた出力は手で直さず再生成対象にする（ValueError）。
    """
    obj = _first_json_object(text)
    if obj is None:
        raise ValueError(f"探索応答からJSONを抽出できませんでした（再生成対象）: {text[:200]}")
    try:
        data = json.loads(obj)
    except json.JSONDecodeError as e:
        raise ValueError(f"探索応答のJSONが壊れています: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("探索応答がJSONオブジェクトではありません")

    resolutions = []
    for r in data.get("resolutions", []):
        if isinstance(r, dict) and "item" in r:
            status = str(r.get("status", "partial"))
            if status not in ("resolved", "partial", "unresolved"):
                status = "partial"
            res = {
                "item": str(r["item"]),
                "status": status,
                "insight": str(r.get("insight", "")),
            }
            # index は必須ではない（1始まりの正整数）。無ければ -1（名前一致にフォールバック）
            try:
                res["index"] = int(r.get("index", -1))
            except (TypeError, ValueError):
                res["index"] = -1
            resolutions.append(res)

    known = [str(k) for k in data.get("known", [])]

    hypotheses = []
    for h in data.get("hypotheses", []):
        if isinstance(h, dict) and "statement" in h:
            hypotheses.append({
                "statement": str(h["statement"]),
                "confidence": _clamp(float(h.get("confidence", 0.5))),
            })

    if not resolutions and not known and not hypotheses:
        raise ValueError("探索応答に有効な項目がありません（再生成対象）")
    return {"resolutions": resolutions, "known": known, "hypotheses": hypotheses}


def _run_explore_step(
    generator: Generator,
    task_prompt: str,
    targets: list[UnknownItem],
    current_state: State,
) -> dict:
    """1回の探索ステップ。形式エラー時はエラー内容をフィードバックして再生成（最大3回）。

    wisdom-council-layer 方式: 崩れたら再生成、手直ししない。
    各項目に番号（1始まり）を付けて渡し、応答の resolutions.index で対応付ける。
    実モデルが item 名を言い換えても、index があれば解決できる（Step 2 修正）。
    """
    target_lines = "\n".join(
        f"{i}. {u.item}（重要度 {u.importance:.2f}, 状態 {u.status}）"
        for i, u in enumerate(targets, start=1)
    )
    base_user = (
        f"テーマ：{task_prompt}\n\n"
        f"既に分かっていること（known）:\n" + (
            "\n".join(f"- {k}" for k in current_state.known) if current_state.known else "（なし）"
        ) +
        f"\n\n分かっていないこと（unknown）— 今回解決を試みる（番号付き）:\n{target_lines}\n\n"
        "上記の unknown の各項目について、専門知識から構造的な分析を行い、"
        "resolved / partial / unresolved を判定してください。\n"
        "resolutions の各項目には、対応する番号（index）を必ず含めること。"
    )
    last_err = ""
    for attempt in range(MAX_ENUMERATION_RETRIES):
        feedback = ""
        if attempt > 0:
            feedback = (
                "\n\n前回の出力は形式エラーでした: "
                f"{last_err}\n説明文を一切付けず、JSONオブジェクトのみを出力してください。"
            )
        raw = generator.generate(system=EXPLORE_STEP_SYSTEM, user=base_user + feedback)
        try:
            return _parse_exploration_result(raw)
        except ValueError as e:
            last_err = str(e)
    raise ValueError(
        f"探索ステップが{MAX_ENUMERATION_RETRIES}回連続で形式エラー（再生成済み）: {last_err}"
    )


def _item_matches(item_a: str, item_b: str) -> bool:
    """探索応答の item と State 内の項目が同一かどうかを判定する。

    - 完全一致、または片方が他方に含まれる（部分文字列）
    - 日本語の言い換え耐性のため、共通の3文字以上連続する部分があれば一致とみなす
      （例:「法規制の境界が曖昧」vs「薬機法・GDPRの法規制」→「法規制」で一致）
    """
    a, b = item_a.strip(), item_b.strip()
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    # 3-gram 共通チェック（短すぎる文字列は誤マッチを防ぐためスキップ）
    if len(a) >= 3 and len(b) >= 3:
        grams = {a[i : i + 3] for i in range(len(a) - 2)}
        for i in range(len(b) - 2):
            if b[i : i + 3] in grams:
                return True
    return False


def _apply_exploration(state: State, result: dict, targets: list[UnknownItem] | None = None) -> str:
    """探索結果を State に反映し、要約文字列を返す。

    対象の特定方法:
      1. resolutions[].index（1始まり）が targets リストの位置を指す場合はそれを使う
      2. index が無い/不正なら item 名で解決（_item_matches の一致判定）
    実モデルが item 名を言い換えても index で確実に結びつく（Step 2 修正）。
    """
    changes: list[str] = []
    targets = targets or []
    for r in result["resolutions"]:
        item = r["item"]
        status = r["status"]
        insight = r.get("insight", "")
        # 1. index による対象特定（1始まり）
        idx = r.get("index", -1)
        resolved_target: UnknownItem | None = None
        if isinstance(idx, int) and 1 <= idx <= len(targets):
            resolved_target = targets[idx - 1]
        # 2. item 名でのフォールバック（言い換え耐性の一致判定）
        #    resolved 済みの項目は対象にしない（探索で status を戻して unknown_level を
        #    増加させないため）
        if resolved_target is None:
            for u in state.unknown:
                if u.status != "resolved" and _item_matches(item, u.item):
                    resolved_target = u
                    break
        target_item = resolved_target.item if resolved_target else item
        if status == "resolved":
            state.resolve_unknown(target_item, "resolved")
            if insight:
                state.add_known(f"{target_item}: {insight}")
            changes.append(f"{target_item}=resolved")
        elif status == "partial":
            state.resolve_unknown(target_item, "partial")
            changes.append(f"{target_item}=partial")
        else:
            changes.append(f"{target_item}=unresolved")
    for k in result["known"]:
        state.add_known(k)
        changes.append(f"known:{k}")
    for h in result["hypotheses"]:
        state.add_hypothesis(h["statement"], h["confidence"])
        changes.append(f"hyp:{h['statement']}")
    state.refresh_derived()
    return "; ".join(changes)


def _build_analysis_context(state: State) -> str:
    """C4 の成果物生成に入力する認知状態（既知・未知・作業仮説）を組み立てる。

    Step 2 修正: B0 は task_prompt のみで生成するのに対し、C4 は列挙・探索で得た
    認知状態を成果物生成に活かす。各 generate() 呼び出しはステートレスであるため、
    成果物生成のモデルに明示的に渡さないと探索の成果が出力に一切反映されない。
    """
    parts: list[str] = []
    if state.known:
        parts.append("【既に分かっていること】\n" + "\n".join(f"- {k}" for k in state.known))
    unresolved = sorted(
        (u for u in state.unknown if u.status != "resolved"),
        key=lambda u: u.importance,
        reverse=True,
    )
    if unresolved:
        parts.append(
            "【分かっていないこと】\n" + "\n".join(f"- {u.item}（重要度 {u.importance:.2f}）" for u in unresolved)
        )
    if state.hypotheses:
        hyp_lines = [f"- {h.statement}（確からしさ {h.confidence:.2f}）" for h in state.hypotheses]
        parts.append("【探索で得られた作業仮説】\n" + "\n".join(hyp_lines))
    if not parts:
        return ""
    return "\n\n" + "\n\n".join(parts)


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
    max_explore_iterations: int = MAX_EXPLORE_ITERATIONS,
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

    # ---- 2.5 探索ループ（decision == "explore" のとき unknown を実際に減らす）----
    # Step 2 で追加。unknown を解消して confidence を上げ、最終的に create に到達できる
    # よう、重要度の高い unknown を順に構造分析で解決していく。
    explore_summary: list[str] = []
    if decision.action == "explore":
        # この試行のループ内で「すでに探索対象にした」項目の item 集合。
        # 同じ項目を何度も探索せず、未探索の項目に進む（Step 2 修正）。
        explored_items: set[str] = set()
        for _ in range(max_explore_iterations):
            # 2.5.1 重要度の高い「未解決 かつ 未探索」の unknown を選択
            targets = [
                u for u in state.unknown
                if u.status != "resolved" and u.item not in explored_items
            ]
            targets.sort(key=lambda u: u.importance, reverse=True)
            targets = targets[:EXPLORE_STEP_SIZE]
            if not targets:
                break
            for t in targets:
                explored_items.add(t.item)

            # 2.5.2 探索ステップ実行（形式エラー時は再生成リトライ）
            try:
                exploration_result = _run_explore_step(generator, task_prompt, targets, state)
            except Exception as e:
                # 3回再生成後も失敗 → 探索を打ち切り、明示的に記録（サイレントドロップ禁止）
                state.history.append(f"EXPLORE_ERROR: {e}")
                explore_summary.append(f"探索エラー: {e}")
                break

            # 2.5.3 State に反映（index で対象を特定できるよう targets を渡す）
            summary = _apply_exploration(state, exploration_result, targets)
            explore_summary.append(summary)

            # 2.5.4 再判定
            decision = orchestrator.decide(state)
            if decision.action != "explore":
                break

        if explore_summary:
            state.history.append("EXPLORE: " + " | ".join(explore_summary))

    # ---- 3. Actionに応じた方針で Analysis Skill 実行 ----
    guidance = ""
    if decision.action == "abstain":
        guidance = ABSTAIN_GUIDANCE
    elif decision.action == "explore":
        guidance = EXPLORE_GUIDANCE

    # 探索で得た認知状態（既知・未知・作業仮説）を成果物生成に渡す。
    # ステートレスな生成器には明示しないと探索の成果が出力に反映されない（Step 2 修正）。
    artifact = generator.generate(
        system=ANALYSIS_SYSTEM + guidance,
        user=task_prompt + _build_analysis_context(state),
    )

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
    "B1": run_b1,
    "B2": run_b2,
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
    max_explore_iterations: int = MAX_EXPLORE_ITERATIONS,
) -> ConditionResult:
    """条件名で実行関数を選ぶ。B0/B1/B2 は C4 用の引数（orchestrator/store）を無視する。"""
    if condition in ("B0", "B1", "B2"):
        runner = RUNNERS[condition]
        return runner(
            generator, evaluator, task_id=task_id, task_prompt=task_prompt,
            pass_threshold=pass_threshold,
        )
    if condition == "C4":
        return run_c4(
            generator, evaluator, orchestrator, store,
            task_id=task_id, task_prompt=task_prompt, pass_threshold=pass_threshold,
            max_explore_iterations=max_explore_iterations,
        )
    raise ValueError(f"未実装の条件: {condition!r}（実装済み: B0, B1, B2, C4）")
