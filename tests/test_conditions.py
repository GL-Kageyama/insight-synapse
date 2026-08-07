"""条件実行モジュール（poc/conditions.py）の単体テスト。

検証対象: 探索ループ（03/00 §3.4 の Explore 継続 / 11/09 §13）
         既知/未知パース・探索結果反映（broken output → regenerate 方針）
"""

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.orchestrator import Orchestrator
from core.state import UnknownItem, new_state
from memory.store import MemoryStore
from poc.conditions import (
    _apply_exploration,
    _item_matches,
    _parse_exploration_result,
    parse_known_unknown,
    run_b1,
    run_b2,
    run_c4,
)


def test_parse_known_unknown_valid():
    text = '{"known": ["市場は拡大傾向"], "unknown": [{"item": "競合", "importance": 0.8, "status": "unresolved"}]}'
    known, unknown = parse_known_unknown(text)
    assert known == ["市場は拡大傾向"]
    assert len(unknown) == 1
    assert unknown[0].item == "競合"
    assert unknown[0].importance == pytest.approx(0.8)


def test_parse_known_unknown_broken_raises():
    """壊れた出力は ValueError → 再生成対象（手で直さない）。"""
    with pytest.raises(ValueError):
        parse_known_unknown("known はこれです")


def test_parse_known_unknown_markdown_wrapped():
    """Markdown で包まれたJSONでも抽出できる（実モデル対策）。"""
    text = '説明文。\n\n```json\n{"known": ["k1"], "unknown": [{"item": "u1", "importance": 0.5, "status": "partial"}]}\n```'
    known, unknown = parse_known_unknown(text)
    assert known == ["k1"]
    assert unknown[0].status == "partial"


def test_parse_exploration_result_valid():
    text = (
        '{"resolutions": [{"item": "競合", "status": "resolved", "insight": "大手3社が参入"}, '
        '{"item": "規制", "status": "partial", "insight": "動向不明"}], '
        '"known": ["新事実"], '
        '"hypotheses": [{"statement": "h1", "confidence": 0.7}]}'
    )
    r = _parse_exploration_result(text)
    assert len(r["resolutions"]) == 2
    assert r["resolutions"][0]["status"] == "resolved"
    assert r["known"] == ["新事実"]
    assert r["hypotheses"][0]["confidence"] == pytest.approx(0.7)


def test_parse_exploration_result_broken_raises():
    with pytest.raises(ValueError):
        _parse_exploration_result("探索しました。成果は得られませんでした。")


def test_parse_exploration_result_empty_raises():
    """resolutions / known / hypotheses が全て空の応答は再生成対象。"""
    with pytest.raises(ValueError):
        _parse_exploration_result('{"resolutions": [], "known": [], "hypotheses": []}')


def test_apply_exploration_updates_state():
    """探索結果を State に反映し、unknown_level が実際に下がる（ループの要）。"""
    st = new_state(
        goal="g",
        unknown=[
            UnknownItem(item="u1", importance=0.8, status="unresolved"),
            UnknownItem(item="u2", importance=0.2, status="unresolved"),
        ],
    )
    assert st.unknown_level == pytest.approx(1.0)
    result = {
        "resolutions": [
            {"item": "u1", "status": "resolved", "insight": "確定"},
            {"item": "u2", "status": "partial", "insight": "一部"},
        ],
        "known": ["外部の新事実"],
        "hypotheses": [{"statement": "h1", "confidence": 0.8}],
    }
    summary = _apply_exploration(st, result)
    # resolved=0, partial=0.5 → (0.8×0 + 0.2×0.5)/(0.8+0.2) = 0.1
    assert st.unknown_level == pytest.approx(0.1)
    assert "u1" in summary
    assert len(st.hypotheses) == 1


def test_apply_exploration_uses_index():
    """index で対象を特定できる（実モデルが item 名を言い換えても解決できる）。"""
    st = new_state(
        goal="g",
        unknown=[
            UnknownItem(item="顧客セグメントの需要が不明", importance=0.8, status="unresolved"),
            UnknownItem(item="競合の動向が不明", importance=0.2, status="unresolved"),
        ],
    )
    targets = [u for u in st.unknown]
    result = {
        "resolutions": [
            # item 名を言い換えても index=1 で「顧客セグメントの需要が不明」を指す
            {"index": 1, "item": "ターゲット顧客の需要", "status": "resolved", "insight": "判明"},
        ],
        "known": [],
        "hypotheses": [],
    }
    summary = _apply_exploration(st, result, targets)
    # (0.8×0 + 0.2×1.0)/(1.0) = 0.2
    assert st.unknown_level == pytest.approx(0.2)
    assert "顧客セグメント" in summary


def test_item_matches_variants():
    """日本語の言い換え耐性: 共通3文字グラムで一致判定される。"""
    assert _item_matches("法規制の境界が曖昧", "薬機法・GDPRの法規制") is True
    assert _item_matches("顧客セグメントの需要", "ターゲット顧客の需要") is True
    # 共通3文字がない（「競合」の2文字のみ）→ 一致しない。このケースは index で対応する
    assert _item_matches("競合の動向", "競合他社の参入状況") is False
    assert _item_matches("収益モデルが未検証", "サブスクリプションの導入") is False


def test_apply_exploration_name_fallback():
    """index が無い場合は item 名の一致でフォールバックする。"""
    st = new_state(
        goal="g",
        unknown=[
            UnknownItem(item="法規制の境界が曖昧", importance=0.8, status="unresolved"),
            UnknownItem(item="収益モデルが未検証", importance=0.2, status="unresolved"),
        ],
    )
    result = {
        "resolutions": [
            # index なし・item 名が言い換えられている → 一致判定（「法規制」）で解決
            {"item": "薬機法・GDPRの法規制", "status": "resolved", "insight": "適用外に設計可能"},
        ],
        "known": [],
        "hypotheses": [],
    }
    summary = _apply_exploration(st, result)
    assert st.unknown_level == pytest.approx(0.2)
    assert "法規制" in summary


def _extract_targets(user: str) -> list[tuple[int, str]]:
    """探索ステップのプロンプトから「番号. 項目名」のリストを抽出する。"""
    return [(int(m.group(1)), m.group(2)) for m in re.finditer(r"(\d+)\. (.+?)（重要度", user)]


def test_build_analysis_context_includes_exploration():
    """探索で得た認知状態（既知・未知・作業仮説）が最終生成プロンプトに反映される。

    Step 2 修正: 各 generate() はステートレスのため、探索の成果（仮説・新たな既知）を
    明示的に渡さないと C4 の成果物生成に一切反映されない。B0 との公正な比較には必須。
    """
    from core.state import UnknownItem, new_state
    from poc.conditions import _build_analysis_context

    st = new_state(
        goal="g",
        known=["市場は拡大傾向", "探索で得た新事実"],
        unknown=[
            UnknownItem(item="競合の動向が不明", importance=0.8, status="unresolved"),
            UnknownItem(item="収益モデルが未検証", importance=0.4, status="partial"),
            UnknownItem(item="規制対応済み", importance=0.2, status="resolved"),
        ],
    )
    st.add_hypothesis("競合は3社参入予定", 0.7)

    ctx = _build_analysis_context(st)
    assert "既に分かっていること" in ctx
    assert "探索で得た新事実" in ctx
    assert "分かっていないこと" in ctx
    assert "競合の動向が不明" in ctx
    assert "収益モデルが未検証" in ctx
    assert "規制対応済み" not in ctx  # resolved は「分かっていないこと」に含めない
    assert "探索で得られた作業仮説" in ctx
    assert "競合は3社参入予定" in ctx


class MockGenerator:
    """生成系Claudeのモック。探索ステップはプロンプトの対象項目を index 付きで resolved にする。"""

    def __init__(self):
        self.calls = []
        self.explore_calls = 0
        self.last_user = ""

    def generate(self, system: str, user: str) -> str:
        self.calls.append(system)
        self.last_user = user
        if "今回解決を試みる" in user:
            self.explore_calls += 1
            targets = _extract_targets(user)
            resolutions = [
                {"index": i, "item": item, "status": "resolved", "insight": "判明"}
                for i, item in targets
            ]
            return json.dumps(
                {
                    "resolutions": resolutions,
                    "known": ["探索で得た新事実"],
                    "hypotheses": [{"statement": "探索で得た作業仮説", "confidence": 0.7}],
                },
                ensure_ascii=False,
            )
        if "JSONオブジェクトだけで整理" in system or "known は既に分かっていること" in user:
            # 既知/未知列挙: unknown_level 0.8 → explore 帯域（0.6〜0.85）
            return (
                '{"known": ["k1"], "unknown": ['
                '{"item": "u1", "importance": 0.6, "status": "unresolved"}, '
                '{"item": "u2", "importance": 0.2, "status": "unresolved"}, '
                '{"item": "u3", "importance": 0.2, "status": "resolved"}]}'
            )
        # 成果物生成
        return "成果物テキスト"


class MockEvaluator:
    """独立評価系統Claudeのモック。合格スコアを返す。"""

    def evaluate(self, system: str, user: str) -> str:
        return '{"quality": 0.9, "logic": 0.9, "creativity": 0.8, "value": 0.9, "risk": 0.1}'


def test_run_c4_exploration_loop_reaches_create(tmp_path):
    """unknown_level 0.8（explore 帯域）でも探索ループで unknown を減らし、create に到達できる。

    Step 1 の失敗要因（探索ループなし→全試行 abstain）が解消されていることの検証。
    """
    generator = MockGenerator()
    evaluator = MockEvaluator()
    store = MemoryStore(tmp_path)
    orch = Orchestrator()  # デフォルト閾値（0.15 / 0.85、Step 2 較正後）

    result = run_c4(
        generator,
        evaluator,
        orch,
        store,
        task_id="t1",
        task_prompt="AIサービスの企画",
        pass_threshold=0.70,
    )
    # 探索ループが実行された（探索ステップが呼ばれた）
    assert generator.explore_calls >= 1
    # 探索で得た認知状態（仮説・新事実）が最終生成のプロンプトに反映される
    assert "探索で得た作業仮説" in generator.last_user
    assert "探索で得た新事実" in generator.last_user
    # 最終判定は create（unknown_level 0.8 → 探索で u1/u2 resolved → 0.0）
    assert result.decision == "create"
    assert result.abstained is False
    assert result.unknown_level == pytest.approx(0.0)
    assert result.success is True


def test_run_c4_exploration_exhausts_items(tmp_path):
    """探索で何も解決できない場合、未探索項目が尽きた時点で break し、explore 判定で最終生成される。

    無限ループ防止の検証。ループは MAX_EXPLORE_ITERATIONS までではなく、
    未解決かつ未探索の項目がなくなった時点で終了する（Step 2 修正）。
    """

    class UnresolvedGen(MockGenerator):
        def generate(self, system: str, user: str) -> str:
            self.calls.append(system)
            if "今回解決を試みる" in user:
                self.explore_calls += 1
                targets = _extract_targets(user)
                # すべて unresolved のまま返す（解決しない）
                resolutions = [
                    {"index": i, "item": item, "status": "unresolved", "insight": "不明"}
                    for i, item in targets
                ]
                return json.dumps(
                    {"resolutions": resolutions, "known": [], "hypotheses": []},
                    ensure_ascii=False,
                )
            if "known は既に分かっていること" in user:
                # 6つの未解決項目（importance 計0.7）+ 1つ解決済み（0.3）→ unknown_level 0.7
                unknown = [
                    {"item": f"u{i}", "importance": 0.1166667, "status": "unresolved"}
                    for i in range(1, 7)
                ]
                unknown.append({"item": "u7", "importance": 0.3, "status": "resolved"})
                return json.dumps({"known": [], "unknown": unknown}, ensure_ascii=False)
            return "成果物テキスト"

    generator = UnresolvedGen()
    evaluator = MockEvaluator()
    store = MemoryStore(tmp_path)
    orch = Orchestrator()  # unknown_level 0.7 → explore 帯域

    result = run_c4(
        generator,
        evaluator,
        orch,
        store,
        task_id="t2",
        task_prompt="AIサービスの企画",
        pass_threshold=0.70,
    )
    # 未解決6項目を 3件×2回で探索し尽くして break（無限ループしない）
    assert generator.explore_calls == 2
    # 解決できず explore のまま最終生成（abstain には落ちない）
    assert result.decision == "explore"
    assert result.abstained is False
    assert result.unknown_level == pytest.approx(0.7)


def test_run_c4_max_explore_iterations_limits_loop(tmp_path):
    """L1 エコノミー（max_explore_iterations=1）では探索ループが1回で打ち切られる。

    thinking_quality=1（開発段階の既定）で素早く試せることを保証する。
    解決しない項目が残っていても、反復上限で停止する（03/00 §3.4 追記の停止条件「上限」）。
    """

    class UnresolvedGen(MockGenerator):
        def generate(self, system: str, user: str) -> str:
            self.calls.append(system)
            if "今回解決を試みる" in user:
                self.explore_calls += 1
                targets = _extract_targets(user)
                resolutions = [
                    {"index": i, "item": item, "status": "unresolved", "insight": "不明"}
                    for i, item in targets
                ]
                return json.dumps(
                    {"resolutions": resolutions, "known": [], "hypotheses": []},
                    ensure_ascii=False,
                )
            if "known は既に分かっていること" in user:
                unknown = [
                    {"item": f"u{i}", "importance": 0.1166667, "status": "unresolved"}
                    for i in range(1, 7)
                ]
                unknown.append({"item": "u7", "importance": 0.3, "status": "resolved"})
                return json.dumps({"known": [], "unknown": unknown}, ensure_ascii=False)
            return "成果物テキスト"

    generator = UnresolvedGen()
    evaluator = MockEvaluator()
    store = MemoryStore(tmp_path)
    orch = Orchestrator()

    # L1 エコノミー: 探索反復 1回で打ち切り（6項目残っていても）
    result = run_c4(
        generator,
        evaluator,
        orch,
        store,
        task_id="t3",
        task_prompt="AIサービスの企画",
        pass_threshold=0.70,
        max_explore_iterations=1,
    )
    assert generator.explore_calls == 1
    assert result.decision == "explore"  # 解決できず explore のまま最終生成


# ---------------- B1: Reflexion ----------------

class SimpleGen:
    """B1/B2 用: 成果物・振り返り・自己批評を返すモック。"""

    def __init__(self):
        self.calls = []

    def generate(self, system: str, user: str) -> str:
        self.calls.append(system)
        if "弱点を正直に振り返って" in system:
            return "ターゲット顧客が曖昧で、価値提案の差別化根拠が不足している。"
        if "問題点を指摘してください" in system:
            return "リスクの検討が不足しており、実現可能性の裏付けがない。"
        return f"成果物#{len(self.calls)}"


class FlipEvaluator:
    """B1 用: 1回目は不合格、2回目は合格のスコアを返すモック。"""

    def __init__(self):
        self.calls = 0

    def evaluate(self, system: str, user: str) -> str:
        self.calls += 1
        if self.calls == 1:
            return '{"quality": 0.5, "logic": 0.5, "creativity": 0.5, "value": 0.5, "risk": 0.5}'
        return '{"quality": 0.9, "logic": 0.9, "creativity": 0.8, "value": 0.9, "risk": 0.1}'


def test_run_b1_reflexes_on_failure():
    """初回失敗 → 振り返り生成 → 再生成 → 再評価（2回生成 + 1回振り返り）。"""
    generator = SimpleGen()
    evaluator = FlipEvaluator()
    result = run_b1(
        generator, evaluator, task_id="b1-1", task_prompt="AIサービスの企画", pass_threshold=0.70,
    )
    assert result.condition == "B1"
    assert result.decision == "reflexion"
    assert result.success is True
    assert evaluator.calls == 2  # 再評価された
    # 振り返りが生成された
    assert any("弱点を正直に振り返って" in c for c in generator.calls)
    assert len(generator.calls) == 3  # 初回生成 + 振り返り + 改善再生成


def test_run_b1_no_reflexion_when_passed():
    """初回で合格 → 振り返りなしで終了。"""
    generator = SimpleGen()
    evaluator = MockEvaluator()  # 常に合格
    result = run_b1(
        generator, evaluator, task_id="b1-2", task_prompt="AIサービスの企画", pass_threshold=0.70,
    )
    assert result.decision == "direct"
    assert result.success is True
    assert not any("弱点を正直に振り返って" in c for c in generator.calls)


# ---------------- B2: Self-Refine ----------------

def test_run_b2_self_refines():
    """初回生成 → 自己批評 → 改善生成 → ブラインド評価。"""
    generator = SimpleGen()
    evaluator = MockEvaluator()
    result = run_b2(
        generator, evaluator, task_id="b2-1", task_prompt="AIサービスの企画", pass_threshold=0.70,
    )
    assert result.condition == "B2"
    assert result.decision == "self_refine"
    assert result.success is True
    # 自己批評が生成された
    assert any("問題点を指摘してください" in c for c in generator.calls)
    # 改善後の成果物は最後の生成物
    assert result.artifact.startswith("成果物#")
    assert len(generator.calls) == 3  # 初回生成 + 自己批評 + 改善生成
