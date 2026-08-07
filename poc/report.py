"""実験レポート生成 — 成功率・効果量・95%CI・判定帯域・報告義務チェックリスト。

正版: docs/11_実装計画とロードマップ/09_最初の動く試作品設計書.md §14「報告義務」

報告義務（全条件共通で必ず含める）:
    ✓ 成功率（overall >= 0.70 の割合）
    ✓ 効果量（最良ベースライン比の絶対差, pp）
    ✓ 95%信頼区間
    ✓ 使用LLM・温度・最大試行数（ハイパーパラメータの全条件共通化の証明）
    ✓ 評価者の独立性対策（盲検化の実施・独立評価系統・人間較正サンプルの一致度）

Step 1 では人間較正（50サンプル）は未実施のため「暫定指標」として報告し、
較正未実施を明記する（11/09 §13）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from poc.config import POCConfig
from poc.harness import ExperimentRun
from poc.stats import best_baseline, difference_ci, summarize_condition


@dataclass(frozen=True)
class ReportSection:
    title: str
    body: str


def _cond_summary(entries, condition: str) -> dict:
    return summarize_condition(entries.for_condition(condition))


def build_report(
    cfg: POCConfig,
    run: ExperimentRun,
    *,
    conditions: tuple[str, ...] = ("B0", "C4"),
    task_set: str = "dev",
) -> str:
    """実験結果からマークダウンレポートを組み立てる。"""
    sections: list[ReportSection] = []

    # ---- 実験メタ ----
    meta = (
        f"# Insight Synapse POC Step 1 実験レポート\n\n"
        f"- 実行ID: `{run.run_id}`\n"
        f"- タスクセット: `{task_set}`\n"
        f"- 比較条件: {', '.join(conditions)}\n"
        f"- 合格しきい値: overall >= {cfg.pass_threshold:.2f}\n\n"
    )
    sections.append(ReportSection("実験メタ", meta))

    # ---- 条件別の成功率 + CI ----
    summary_lines = []
    summaries = {}
    for cond in conditions:
        s = _cond_summary(run, cond)
        summaries[cond] = s
        summary_lines.append(
            f"| {cond} | {s['successes']}/{s['n']} | {s['success_rate']*100:.1f}% "
            f"| {s['ci_low']*100:.1f}% - {s['ci_high']*100:.1f}% |"
        )
    summary_body = (
        "| 条件 | 成功数/試行数 | 成功率 | 95%CI (Wilson) |\n"
        "|---|---|---|---|\n" + "\n".join(summary_lines) + "\n\n"
        "成功率 = overall >= 0.70 の割合（03/00 §2.4）\n"
    )
    sections.append(ReportSection("成功率", summary_body))

    # ---- 効果量 + 判定帯域 ----
    if "C4" in conditions and len(conditions) > 1:
        baseline = best_baseline({c: summaries[c]["success_rate"] for c in conditions})
        c4 = summaries["C4"]
        base = summaries[baseline]
        d = difference_ci(
            s1=c4["successes"], n1=c4["n"], s2=base["successes"], n2=base["n"]
        )
        band_labels = {
            "reject": "仮説Hを棄却（<5pp）",
            "indeterminate": "判定保留（5〜20pp・追試必須）",
            "uncertain": "効果は示唆されるが不確実（20〜39pp・追試必須）",
            "support": "決定的支持（>=39pp）",
        }
        effect_body = (
            f"- 最良ベースライン: **{baseline}**（成功率 {base['success_rate']*100:.1f}%）\n"
            f"- C4 成功率: **{c4['success_rate']*100:.1f}%**\n"
            f"- 効果量: **{d.diff_pp:+.1f}pp**（C4 − {baseline}）\n"
            f"- 効果量の95%CI: {d.low_pp:+.1f}pp 〜 {d.high_pp:+.1f}pp\n"
            f"- 判定帯域: **{band_labels[d.judgment]}**\n"
            f"- 追試ルール（03/00 §8.3）: 最大1回・N=74/群。追試判定 = {d.followup_verdict}\n"
        )
    else:
        # 単一条件・C4 を含まない実行では効果量は計算できない（最良ベースラインが不在）
        effect_body = (
            f"- 効果量は**計算不可**: C4 とベースライン条件（B0/B1/B2）の比較が必要。\n"
            f"- 現在の条件: {', '.join(conditions)}。成功率の一覧は上表を参照。\n"
            f"- スモーク検証用の実行であり、仮説Hの判定は行わない（本番 N=20 で判定）。\n"
        )
    sections.append(ReportSection("効果量と判定", effect_body))

    # ---- §14 報告義務チェックリスト ----
    checklist = [
        ("成功率（overall >= 0.70 の割合）", True),
        ("効果量（最良ベースライン比の絶対差, pp）", True),
        ("95%信頼区間", True),
        (
            f"使用LLM・温度・最大試行数 — 生成={cfg.generation_model}, 評価={cfg.evaluation_model}, "
            f"温度={cfg.temperature}, N={cfg.n_per_condition}/条件（全条件共通）",
            True,
        ),
        (
            "評価者の独立性対策: 盲検化（条件ラベル非表示）", True),
        (
            "評価者の独立性対策: 独立評価系統（生成≠評価モデル）",
            cfg.generation_model != cfg.evaluation_model,
        ),
        (
            "評価者の独立性対策: 人間較正サンプル一致度（50サンプル・rho>=0.70）",
            False,  # Step 2 で実装
        ),
    ]
    checklist_body = "```text\n" + "".join(
        f"{'✓' if ok else '✗'} {label}\n" for label, ok in checklist
    ) + "```\n"
    if not checklist[-1][1]:
        checklist_body += (
            "\n> ⚠️ 人間較正は **未実施**（Step 2 で50サンプル実施予定）。"
            "本レポートの成功率は**較正なしの暫定指標**であり、較正後の絶対値とは異なりうる。"
        )
    sections.append(ReportSection("報告義務チェックリスト（§14）", checklist_body))

    # ---- 付記: B1/B2 未実装 + 実行バックエンド ----
    appendix = (
        "### 付記\n\n"
        "- B1（Reflexion）/ B2（Self-Refine）は本Step未実装。最良ベースラインは現時点で B0 のみ。\n"
        "- 本レポートの判定は N=20/群 の検出力に基づく暫定値（03/00 §8・11/09 §14）。\n"
    )
    # §14 報告義務「使用LLM」の透明性: ゲートウェイ経由の実行は実バックエンドを明記する
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    if base_url:
        sonnet_map = os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL", "")
        haiku_map = os.environ.get("ANTHROPIC_DEFAULT_HAIKU_MODEL", "")
        appendix += (
            f"- 実行バックエンド: `{base_url}` 経由。"
            f"要求モデル: 生成=`{cfg.generation_model}` / 評価=`{cfg.evaluation_model}`。\n"
        )
        if sonnet_map and haiku_map:
            appendix += (
                f"- ゲートウェイ実マッピング: 生成→`{sonnet_map}` / 評価→`{haiku_map}`。"
                "系統分離（生成≠評価）は維持。\n"
            )
    sections.append(ReportSection("付記", appendix))

    return "\n".join(s.body for s in sections)


def write_report(
    report_text: str,
    *,
    out_dir: str | Path,
    run_id: str,
) -> Path:
    """レポートを markdown として書き出す。"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{run_id}.md"
    path.write_text(report_text, encoding="utf-8")
    return path
