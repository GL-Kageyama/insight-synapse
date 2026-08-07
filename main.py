"""Insight Synapse POC Step 1 — 対照実験のエントリーポイント。

使用例:
    python main.py --condition=B0 --tasks=5          # 1条件だけスモーク
    python main.py --compare=B0,C4 --tasks=5          # 2条件比較（開発用）
    python main.py --all --tasks=20 --per-condition=1 # 本番（20問×1回/条件）
    python main.py --compare=B0,C4 --mock             # API不要でパイプライン検証

注意:
    - APIキーは ANTHROPIC_API_KEY 環境変数（または .env）から読み取る
    - --mock は決定論的モックでAPIを呼ばず、パイプライン全体を検証できる
    - 本番の効果量計算には config/params.yaml（03/00正版）の数値を使用する
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_REPO_ROOT))

from adapters.claude_client import ClaudeClient, ClaudeConfig  # noqa: E402
from core.orchestrator import Orchestrator  # noqa: E402
from memory.store import MemoryStore  # noqa: E402
from poc.config import POCConfig  # noqa: E402
from poc.harness import Harness  # noqa: E402
from poc.report import build_report, write_report  # noqa: E402
from poc.stats import best_baseline, difference_ci, summarize_condition  # noqa: E402
from poc.tasks import head_tasks  # noqa: E402

IMPLEMENTED_CONDITIONS = ("B0", "C4")


class MockClaude:
    """スモークラン用の決定論的モック。APIキー不要で全パイプラインを通す。

    generate は呼び分け（unknown列挙 / 分析成果物）をシステムプロンプトで判定し、
    evaluate は固定の5軸スコアを返す。
    """

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)
        self.calls = {"generate": 0, "evaluate": 0}

    def generate(self, system: str, user: str) -> str:
        self.calls["generate"] += 1
        if "既に分かっていること" in system or "分かっていること" in system:
            # C4: known/unknown 列挙（unknown_level=0.85 → abstain 経路を必ず通す）
            return json.dumps(
                {
                    "known": ["AIサービスの市場は競争が激しい"],
                    "unknown": [
                        {"item": "具体的な顧客セグメントの需要", "importance": 0.7, "status": "unresolved"},
                        {"item": "競合との差別化要因", "importance": 0.3, "status": "partial"},
                    ],
                },
                ensure_ascii=False,
            )
        # 分析成果物
        return (
            "# 分析成果物（モック）\n\n"
            "## Target\nAIサービスを導入したい事業者。\n"
            "## Value\n業務効率の向上。\n"
            "## Risk\n初期コスト。\n"
            "## Opportunity\n市場成長。"
        )

    def evaluate(self, system: str, user: str) -> str:
        self.calls["evaluate"] += 1
        # overall = 0.7075 >= 0.70 → Pass（スモークで成功経路を通す）
        return '{"quality": 0.8, "logic": 0.7, "creativity": 0.6, "value": 0.75, "risk": 0.4}'


def _load_dotenv(path: Path = _REPO_ROOT / ".env") -> None:
    """最小の .env ローダー（依存なし）。既存の環境変数は上書きしない。"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Insight Synapse POC Step 1 対照実験")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--condition", "-c", help="単一条件で実行（B0 または C4）")
    g.add_argument("--compare", help="複数条件を比較（例: B0,C4）")
    g.add_argument("--all", action="store_true", help=f"全実装条件（{','.join(IMPLEMENTED_CONDITIONS)}）")
    p.add_argument("--tasks", "-t", type=int, default=5, help="使用タスク数（既定5=開発用セット）")
    p.add_argument("--taskset", default="dev", choices=["dev", "prod"], help="タスクセット（dev/prod）")
    p.add_argument("--per-condition", type=int, default=2, help="条件あたりのリピート数（本番 N=20 は 20問×1回）")
    p.add_argument("--seed", type=int, default=42, help="カウンターバランス用シード")
    p.add_argument("--mock", action="store_true", help="APIを呼ばない決定論的モックで実行")
    p.add_argument("--out-dir", default="evaluation/reports", help="レポート・実験ログの出力先")
    return p.parse_args(argv)


def resolve_conditions(args: argparse.Namespace) -> list[str]:
    if args.all:
        conds = list(IMPLEMENTED_CONDITIONS)
    elif args.compare:
        conds = [c.strip() for c in args.compare.split(",")]
    else:
        conds = [args.condition]
    unknown = [c for c in conds if c not in IMPLEMENTED_CONDITIONS]
    if unknown:
        raise SystemExit(f"未実装の条件: {unknown}（実装済み: {IMPLEMENTED_CONDITIONS}）")
    if len(set(conds)) != len(conds):
        raise SystemExit("条件の重複があります")
    return conds


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    args = parse_args(argv)
    cfg = POCConfig.load()

    conditions = resolve_conditions(args)
    tasks = head_tasks(args.tasks, args.taskset)

    # ---- 生成系 / 評価系 Claude の構築（--mock ならAPI不要） ----
    if args.mock:
        mock = MockClaude(seed=args.seed)
        generator = mock
        evaluator = mock
    else:
        try:
            claude_cfg = ClaudeConfig(
                api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
                auth_token=os.environ.get("ANTHROPIC_AUTH_TOKEN", ""),
                base_url=os.environ.get("ANTHROPIC_BASE_URL", ""),
                generation_model=cfg.generation_model,
                evaluation_model=cfg.evaluation_model,
                temperature=cfg.temperature,
            )
            client = ClaudeClient(claude_cfg)
        except ValueError as e:
            raise SystemExit(
                f"{e}\n環境変数 ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN を設定するか、"
                "--mock でスモークランしてください。"
            )
        generator = client
        evaluator = client

    # ---- 実験コンポーネント構築 ----
    orchestrator = Orchestrator(
        abstain_confidence_lt=cfg.abstain_confidence_lt,
        abstain_unknown_level_ge=cfg.abstain_unknown_level_ge,
        explore_unknown_level_ge=cfg.explore_unknown_level_ge,
        create_confidence_ge=cfg.create_confidence_ge,
        create_unknown_level_le=cfg.create_unknown_level_le,
    )
    store = MemoryStore(_REPO_ROOT / "memory")
    harness = Harness(
        generator=generator,
        evaluator=evaluator,
        orchestrator=orchestrator,
        store=store,
        experiment_dir=_REPO_ROOT / args.out_dir,
        pass_threshold=cfg.pass_threshold,
        seed=args.seed,
    )

    # ---- 実行 ----
    total_trials = len(conditions) * len(tasks) * args.per_condition
    print(f"[実行] 条件={conditions} タスク={len(tasks)}問 リピート={args.per_condition} 計{total_trials}試行")
    run = harness.run(conditions, tasks, n_reps=args.per_condition)

    # ---- 結果サマリ ----
    print("\n=== 成功率 ===")
    summaries = {c: summarize_condition(run.for_condition(c)) for c in conditions}
    for c in conditions:
        s = summaries[c]
        print(f"  {c}: {s['successes']}/{s['n']} = {s['success_rate']*100:.1f}% "
              f"(95%CI {s['ci_low']*100:.1f}-{s['ci_high']*100:.1f})")
    if "C4" in summaries and len(summaries) > 1:
        baseline = best_baseline({c: s["success_rate"] for c, s in summaries.items()})
        c4, base = summaries["C4"], summaries[baseline]
        d = difference_ci(c4["successes"], c4["n"], base["successes"], base["n"])
        print(f"\n=== 効果量 ===")
        print(f"  最良ベースライン={baseline} vs C4: {d.diff_pp:+.1f}pp "
              f"(95%CI {d.low_pp:+.1f}〜{d.high_pp:+.1f}) 判定={d.judgment}")

    # ---- レポート出力 ----
    report = build_report(cfg, run, conditions=tuple(conditions), task_set=args.taskset)
    path = write_report(report, out_dir=_REPO_ROOT / args.out_dir, run_id=run.run_id)
    print(f"\n[レポート] {path}")
    if args.mock:
        print(f"[モック] 呼び出し: 生成={mock.calls['generate']}回 評価={mock.calls['evaluate']}回")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
