# Insight Synapse
## API Interface Design Specification
### APIインターフェース設計書 v0.1

---

# 1. 目的

本ドキュメントは、Insight Synapse内部コンポーネント間の通信仕様を定義する。

目的：

> 各Layerの責務を保ちながら、思考・判断・制作・評価・記憶の循環を実現する。

---

# 2. API設計思想

Insight Synapseでは、

「直接呼び出し」

を避ける。

---

悪い構造：

```text
Skill

↓

Memory直接操作
```

---

良い構造：

```text
Skill

↓

Orchestrator

↓

Memory Service
```

---

# 3. 通信モデル

基本構造：

```text
Human

↓

Interface API

↓

Orchestrator API

↓

Workflow API

↓

Skill API

↓

Evaluation API

↓

Memory API
```

---

# 4. 共通データ形式

全API共通：

```json
{
  "request_id": "",
  "timestamp": "",
  "source": "",
  "payload": {}
}
```

---

Response：

```json
{
  "request_id": "",
  "status": "success",
  "result": {},
  "trace_id": ""
}
```

---

# 5. Goal Input API

## 目的

人間から目的を受け取る。

---

Endpoint:

```http
POST /goal
```

---

Request:

```json
{
  "goal":
  "新しいサービス案を作成する"
}
```

---

Response:

```json
{
  "goal_id":
  "goal_001",

  "status":
  "received"
}
```

---

# 6. State API

## 目的

現在状態を取得・更新する。

---

## Get State

```http
GET /state
```

---

Response:

```json
{
 "phase":"research",
 "confidence":0.45,
 "unknown":0.7
}
```

---

## Update State

```http
POST /state/update
```

---

Request:

```json
{
 "phase":"creation"
}
```

---

# 7. Orchestrator API

## 目的

次の行動を判断する。

---

Endpoint:

```http
POST /decision
```

---

Request:

```json
{
 "goal":"",
 "state":"",
 "memory_context":""
}
```

---

Response:

```json
{
 "action":
 "research",

 "reason":
 "unknown level is high",

 "confidence":
 0.8
}
```

---

# 8. Workflow API

## 目的

処理フローを実行する。

---

Endpoint:

```http
POST /workflow/run
```

---

Request:

```json
{
 "workflow":
 "creation"
}
```

---

Response:

```json
{
 "steps":

 [
 "research",
 "structure",
 "create",
 "evaluate"
 ]
}
```

---

# 9. Skill API

## 目的

能力を実行する。

---

Endpoint:

```http
POST /skill/run
```

---

Request:

```json
{
 "skill":
 "create",

 "input":
 "企画案"
}
```

---

Response:

```json
{
 "artifact":
 "",
 "trace_id":""
}
```

---

# 10. Primitive API

## 目的

基本思考操作を実行する。

---

Endpoint:

```http
POST /primitive/run
```

---

Request:

```json
{
 "primitive":
 "abstract",

 "input":
 "複数事例"
}
```

---

Response:

```json
{
 "output":
 "共通概念"
}
```

---

# 11. Evaluation API

## 目的

成果物を評価する。

---

Endpoint:

```http
POST /evaluate
```

---

Request:

```json
{
 "artifact":"",
 "criteria":
 [
 "quality",
 "value"
 ]
}
```

---

Response:

```json
{
 "score":8.2,

 "strength":
 "独自性",

 "weakness":
 "検証不足"
}
```

---

# 12. Memory API

## 目的

経験を保存・取得する。

---

## Save Memory

```http
POST /memory/save
```

---

Request:

```json
{
"type":
"decision",

"content":
"調査を優先した"
}
```

---

## Search Memory

```http
POST /memory/search
```

---

Request:

```json
{
"query":
"過去の類似判断"
}
```

---

Response:

```json
{
"patterns":
[]
}
```

---

# 13. Trace API

## 目的

思考軌跡保存。

---

Endpoint:

```http
POST /trace/save
```

---

Request:

```json
{
"question":"",
"analysis":"",
"decision":""
}
```

---

# 14. Human Approval API

## 目的

重要判断への人間介入。

---

Endpoint:

```http
POST /approval
```

---

Request:

```json
{
"decision_id":"",
"action":
"approve"
}
```

---

Response:

```json
{
"status":
"approved"
}
```

---

# 15. エラー処理

全API共通。

```json
{
"status":
"error",

"error_type":
"",

"message":
"",

"trace_id":
""
}
```

---

# 16. API実行フロー例

サービス企画の場合：

```text
Goal API

↓

State API

↓

Decision API

↓

Workflow API

↓

Skill API

↓

Evaluation API

↓

Memory API
```

---

# 17. APIとMemory連携

重要ルール：

すべての重要API実行はTraceを残す。

```text
API Call

↓

Trace

↓

Evaluation

↓

Memory
```

---

# 18. MVP API範囲

最初に実装：

```text
✓ /goal

✓ /state

✓ /decision

✓ /skill/run

✓ /evaluate

✓ /memory/save
```

---

後回し：

```text
× Agent API

× Marketplace API

× Distributed Memory API
```

---

# 19. API設計原則

## 原則1

Layer間依存を減らす。

---

## 原則2

すべての判断は追跡可能にする。

---

## 原則3

データ形式を長期保存可能にする。

---

## 原則4

将来拡張可能な境界を作る。

---

# 20. 最終定義

Insight Synapse API Interfaceとは、

> AI内部の思考・判断・制作・評価・記憶を分離しながら接続するための通信基盤である。

APIの役割は単なるデータ交換ではない。

**知能の各機能を協調させる神経系である。**