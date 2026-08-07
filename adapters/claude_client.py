"""Claude API クライアント（第一アダプタ）。

生成（Skill）と評価（Evaluation Engine）で**必ず別モデル系統**を使う。
POC設計書 §13「評価者の独立性（自己評価の循環の遮断）」の実装の中核。
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import anthropic

# モデル系統（03/00 §2.6 / 11/09 §13: 独立評価系統）
# 生成と評価で異なるモデル系統を使う。両者が同一だと循環評価になるため禁止。
DEFAULT_GENERATION_MODEL = "claude-sonnet-4-5"
DEFAULT_EVALUATION_MODEL = "claude-haiku-4-5"


@dataclass
class ClaudeConfig:
    api_key: str
    generation_model: str = DEFAULT_GENERATION_MODEL
    evaluation_model: str = DEFAULT_EVALUATION_MODEL
    max_tokens: int = 4096
    temperature: float = 0.0
    max_retries: int = 3

    def validate_lineage_separation(self) -> None:
        """生成系と評価系の系統分離を保証する（同一系統は循環評価を招く）。"""
        if self.generation_model == self.evaluation_model:
            raise ValueError(
                "generation_model と evaluation_model が同一です。"
                "独立評価系統（11/09 §13）を保つため異なるモデルを指定してください。"
            )


class ClaudeClient:
    """Anthropic SDK の薄いラッパー。系統分離をAPIで強制する。

    - `generate()` … Skill（生成）専用。生成系モデルを使用
    - `evaluate()` … Evaluation Engine（評価）専用。評価系モデルを使用
    """

    def __init__(self, config: ClaudeConfig | None = None):
        config = config or self._default_config()
        config.validate_lineage_separation()
        self.config = config
        self.client = anthropic.Anthropic(api_key=config.api_key)

    @staticmethod
    def _default_config() -> ClaudeConfig:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY が設定されていません。"
                ".env または環境変数で設定してください（.env.example 参照）。"
            )
        return ClaudeConfig(api_key=api_key)

    def generate(self, system: str, user: str) -> str:
        """生成系モデルで呼び出す（Skill: Analysis 用）。"""
        return self._call(self.config.generation_model, system, user)

    def evaluate(self, system: str, user: str) -> str:
        """評価系モデルで呼び出す（Evaluation Engine 用）。"""
        return self._call(self.config.evaluation_model, system, user)

    def _call(self, model: str, system: str, user: str) -> str:
        last_err: Exception | None = None
        for attempt in range(self.config.max_retries):
            try:
                response = self.client.messages.create(
                    model=model,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                return "".join(
                    b.text for b in response.content if getattr(b, "type", "") == "text"
                )
            except (anthropic.APIStatusError, anthropic.APIConnectionError, anthropic.APITimeoutError) as e:
                last_err = e
                if attempt < self.config.max_retries - 1:
                    time.sleep(2**attempt)  # 指数バックオフ
        raise RuntimeError(f"Claude API 呼び出しに失敗しました: {last_err}") from last_err
