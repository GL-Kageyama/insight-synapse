"""POC実行コンフィグ — config/params.yaml のロード。

config/params.yaml は docs/03_コアコンポーネント/00_数値定義書.md の実行時プレイバック。
このモジュールが全コンポーネントに数値を供給する（単一管理）。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PARAMS_PATH = _REPO_ROOT / "config" / "params.yaml"


@dataclass
class POCConfig:
    params: dict[str, Any]

    # ---- 評価（03/00 §2） ----
    @property
    def criteria(self) -> dict[str, float]:
        return self.params["criteria"]

    @property
    def pass_threshold(self) -> float:
        return self.params["thresholds"]["pass"]

    @property
    def revise_threshold(self) -> float:
        return self.params["thresholds"]["revise"]

    # ---- 棄権機構（03/00 §3.5） ----
    @property
    def abstain_confidence_lt(self) -> float:
        return self.params["abstention"]["confidence_lt"]

    @property
    def abstain_unknown_level_ge(self) -> float:
        return self.params["abstention"]["unknown_level_ge"]

    # ---- 判断しきい値（03/00 §3.4） ----
    @property
    def explore_unknown_level_ge(self) -> float:
        return self.params["decision"]["explore_when_unknown_level_ge"]

    @property
    def create_confidence_ge(self) -> float:
        return self.params["decision"]["create_when_confidence_ge"]

    @property
    def create_unknown_level_le(self) -> float:
        return self.params["decision"]["create_when_unknown_level_le"]

    # ---- 実験統計（03/00 §8） ----
    @property
    def alpha(self) -> float:
        return self.params["stats"]["alpha"]

    @property
    def n_per_condition(self) -> int:
        return self.params["stats"]["n_per_condition"]

    @property
    def followup_n(self) -> int:
        return self.params["stats"]["followup_n"]

    @property
    def judgment_bands(self) -> dict[str, float]:
        return self.params["judgment_bands"]

    # ---- Claude（生成/評価の系統分離） ----
    @property
    def generation_model(self) -> str:
        return self.params["claude"]["generation_model"]

    @property
    def evaluation_model(self) -> str:
        return self.params["claude"]["evaluation_model"]

    @property
    def temperature(self) -> float:
        return self.params["claude"]["temperature"]

    @classmethod
    def load(cls, path: str | Path = DEFAULT_PARAMS_PATH) -> "POCConfig":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"パラメータ定義が見つかりません: {path}")
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        cfg = cls(params=raw)
        cfg.validate()
        return cfg

    def validate(self) -> None:
        """数値の整合性チェック。正版（03/00）からの逸脱を実行前に検出する。"""
        w = self.criteria
        if abs(sum(w.values()) - 1.0) > 1e-9:
            raise ValueError(f"評価5軸の重みの合計が1.0でありません: {sum(w.values())}")
        if self.generation_model == self.evaluation_model:
            raise ValueError("生成系と評価系のモデルが同一です（独立評価系統の違反）")
        if not (0.0 <= self.pass_threshold <= 1.0):
            raise ValueError(f"pass_threshold が範囲外: {self.pass_threshold}")
