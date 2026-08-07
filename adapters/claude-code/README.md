# adapters/claude-code/

**第一アダプタ**。コア抽象を Markdown + YAML + Git + Skill にマッピングする。

正版: `docs/10_環境とリポジトリ/02_最終リポジトリ構成仕様書.md` §4・§8・`docs/11_実装計画とロードマップ/04_Claude_Code統合仕様書.md`
状態: 骨格のみ

| ディレクトリ | 責務 |
|---|---|
| `skills/` | Runtime固有のSkill |
| `commands/` | Runtime固有のコマンド |
| `.claude/` | Claude Code設定 |
