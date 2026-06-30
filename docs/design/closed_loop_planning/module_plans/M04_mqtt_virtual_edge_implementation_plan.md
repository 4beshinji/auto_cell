# M04 MQTT / Gateway / Virtual Edge 実装計画

> **Scope**: auto_cell A 層（iPSC 浮遊/凝集体バイオリアクター制御）Phase 1 における、ブレイン ⇄ デバイス（`plant_model`）の通信層。
> **目的**: `05_implementation_plan_phase1.md` Sprint 6 の D1–D4（MQTT topic 契約・MQTT client・correlation_id 管理・冪等性・`infra/virtual_edge/dummy_bioreactor.py`）を、実装者が即座にコーディングを始められる粒度で設計する。
> **前提文書**: `05_implementation_plan_phase1.md`、`06_critical_path_and_work_order.md`、`03_swarm_findings_integration.md`、`02_missing_assets_for_closed_loop.md`、`../kg_to_auto_cell.md`（§7.1 LADS/SiLA2、§7.3 MQTT topic 契約）

---

## 1. 目標と成功基準

1. ブレインと `plant_model`（`infra/virtual_edge/dummy_bioreactor.py`）が MQTT 経由で閉ループを回せる。
2. コマンド/ACK の request-response に MQTT 5.0 の `Response Topic` + `Correlation Data` を使い、cmd/ack/approval/event_store を紐付けられる。
3. `request_id` による重複実行防止（冪等性）と `Message Expiry Interval` を実装する。
4. LADS/OPC-UA、SiLA2 の抽象骨格を用意し、将来の実機 gateway 差替を `gateway/` 配下で閉じる。
5. `pytest tests/test_mqtt_*.py`、`tests/test_virtual_edge.py` が pass する。

---

## 2. ファイル構成

```
src/auto_cell/gateway/
├── __init__.py
├── mqtt_client.py              # paho-mqtt v2 ベース publisher/subscriber
├── request_response.py         # MQTT 5.0 Response Topic/Correlation Data 付き request-response
├── correlation.py              # correlation_id / request_id 生成・管理
├── idempotency.py              # request_id による重複実行防止 + TTL
├── lads_opcua_client.py      # LADS Functional Unit / Function 抽象 + OPC-UA 接続骨格
└── sila_client.py              # SiLA2 Feature 抽象 + クライアント骨格

infra/virtual_edge/
├── __init__.py
├── dummy_bioreactor.py         # MQTT 経由で plant_model.step() を駆動する仮想バイオリアクター
└── device_profile.py           # チャネル/ツール → LADS Function マッピング stub

config/
└── mqtt_topics.yaml            # topic テンプレートと QoS/retain 設定

tests/
├── conftest.py                 # MQTT テストブローカー fixture（amqtt 想定）
├── test_mqtt_client.py
├── test_mqtt_idempotency.py
└── test_virtual_edge.py
```

---

## 3. MQTT topic 契約

名前空間は `cell/{culture_unit_id}/...`（`kg_to_auto_cell.md` §7.3 決定）。`device_id`/`function_id` は LADS Function 名と一致させ、gateway の機械変換を薄くする。

### 3.1 topic 一覧

| # | topic | 方向 | 用途 | QoS | retain |
|---|---|---|---|---|---|
| 1 | `cell/{cu}/telemetry/{device_id}/{function_id}` | gateway → brain | 連続センサ値 | 1 | ✅ |
| 2 | `cell/{cu}/telemetry/{device_id}/all` | gateway → brain | 全センサまとめ | 1 | ✅ |
| 3 | `cell/{cu}/event/{source}/{event_type}` | gateway/brain → HMI/event_store | イベント/アラーム | 1 | ❌ |
| 4 | `cell/{cu}/cmd/{device_id}/{function_id}` | brain → gateway | 副作用コマンド | 1 | ❌ |
| 5 | `cell/{cu}/ack/{device_id}/{function_id}` | gateway → brain | コマンド受理/結果 | 1 | ❌ |
| 6 | `cell/{cu}/program/{device_id}/request` | brain → gateway | LADS Program 投入・レシピアップロード | 1 | ❌ |
| 7 | `cell/{cu}/program/{device_id}/response` | gateway → brain | Program 完了/結果 | 1 | ❌ |
| 8 | `cell/{cu}/state/approval/{request_id}` | gateway/brain → HMI | 承認要求状態遷移 | 1 | ✅ |
| 9 | `cell/{cu}/state/device/{device_id}` | gateway → HMI/brain | デバイス接続/モード状態 | 1 | ✅ |
| 10 | `cell/{cu}/state/run/{run_id}` | brain → HMI | 現在 run 状態 | 1 | ✅ |
| 11 | `cell/{cu}/notify/hmi/{priority}` | brain/gateway → HMI | 通知（P0–P3） | 1 | ❌ |
| 12 | `cell/{cu}/hmi/approval/{request_id}` | HMI → brain/gateway | 承認/拒否/キャンセル | 1 | ❌ |
| 13 | `cell/{cu}/hmi/command/{command_name}` | HMI → brain | HMI からの制御（hold/resume） | 1 | ❌ |

### 3.2 ペイロード例

```yaml
# 1. telemetry
# topic: cell/cu_001/telemetry/bioreactor_01/ph
ts: "2026-06-30T07:37:21.384Z"
value: 7.10
unit: "pH"
quality: "GOOD"          # GOOD, UNCERTAIN, BAD
source: "bioreactor_01"

# 2. telemetry/all
# topic: cell/cu_001/telemetry/bioreactor_01/all
ts: "2026-06-30T07:37:21.384Z"
values:
  ph: 7.10
  do_percent: 40.0
  vcd: 0.5e6
  viability: 0.98

# 3. event
# topic: cell/cu_001/event/brain/glucose_low
ts: "2026-06-30T07:37:21.384Z"
source: "brain"
event_type: "glucose_low"
severity: "P1"           # P0=即時停止, P1=Warning, P2=参考, P3=info
message: "glucose 1.65 mM <= warning 1.8 mM"
correlation_id: "c_abc123"

# 4. cmd
# topic: cell/cu_001/cmd/bioreactor_01/set_perfusion_rate
args:
  vvd: 1.5
correlation_id: "c_abc123"
request_id: "req_abc123"
ts: "2026-06-30T07:37:21.384Z"
source: "brain"
response_topic: "cell/cu_001/ack/bioreactor_01/set_perfusion_rate"
message_expiry_interval: 60

# 5. ack
# topic: cell/cu_001/ack/bioreactor_01/set_perfusion_rate
status: "accepted"       # accepted, completed, failed, replayed, timeout
result:
  vvd: 1.5
  previous: 0.0
correlation_id: "c_abc123"
request_id: "req_abc123"
ts: "2026-06-30T07:37:21.384Z"
source: "bioreactor_01"

# 6. program/request
# topic: cell/cu_001/program/bioreactor_01/request
program_id: "passage_routine_v1"
recipe: { ... }
correlation_id: "c_def456"
request_id: "req_def456"
ts: "2026-06-30T07:37:21.384Z"

# 7. program/response
# topic: cell/cu_001/program/bioreactor_01/response
status: "completed"
result:
  aggregate_diameter_um: 180.0
correlation_id: "c_def456"
request_id: "req_def456"
ts: "2026-06-30T07:37:21.384Z"

# 8. state/approval
# topic: cell/cu_001/state/approval/req_xyz789
request_id: "req_xyz789"
correlation_id: "c_xyz789"
state: "requested"        # requested → approved|rejected|pending_timeout → executed|cancelled
requested_by: "brain"
requested_action:
  tool: "set_perfusion_rate"
  args:
    vvd: 8.5              # 包絡線外のため承認必要
ts: "2026-06-30T07:37:21.384Z"
expires_at: "2026-06-30T07:47:21.384Z"

# 9. notify/hmi
# topic: cell/cu_001/notify/hmi/P0
priority: "P0"
message: "contamination_suspected: stop immediately"
source: "brain"
ts: "2026-06-30T07:37:21.384Z"
correlation_id: "c_ghi789"

# 10. hmi/approval
# topic: cell/cu_001/hmi/approval/req_xyz789
request_id: "req_xyz789"
decision: "approved"      # approved / rejected / cancelled
operator_id: "tanaka@lab"
reason: "confirmed by supervisor"
ts: "2026-06-30T07:40:00.000Z"
```

### 3.3 `config/mqtt_topics.yaml`

```yaml
# MQTT topic 契約テンプレート
# プレースホルダ: {cu}=culture_unit_id, {device_id}, {function_id}, {request_id}, {priority}
namespace: "cell"
topics:
  telemetry_single: "cell/{cu}/telemetry/{device_id}/{function_id}"
  telemetry_all:    "cell/{cu}/telemetry/{device_id}/all"
  event:            "cell/{cu}/event/{source}/{event_type}"
  cmd:              "cell/{cu}/cmd/{device_id}/{function_id}"
  ack:              "cell/{cu}/ack/{device_id}/{function_id}"
  program_request:  "cell/{cu}/program/{device_id}/request"
  program_response: "cell/{cu}/program/{device_id}/response"
  state_approval:   "cell/{cu}/state/approval/{request_id}"
  state_device:     "cell/{cu}/state/device/{device_id}"
  state_run:        "cell/{cu}/state/run/{run_id}"
  notify_hmi:       "cell/{cu}/notify/hmi/{priority}"
  hmi_approval:     "cell/{cu}/hmi/approval/{request_id}"
  hmi_command:      "cell/{cu}/hmi/command/{command_name}"

qos:
  telemetry: 1
  event: 1
  cmd: 1
  ack: 1
  program: 1
  state: 1
  notify: 1
  hmi: 1

retain:
  telemetry_single: true
  telemetry_all: true
  state_approval: true
  state_device: true
  state_run: true
  # cmd/event/ack/notify/hmi は retain=false
```

---

## 4. MQTT client（paho-mqtt v2）

`paho-mqtt>=2.1`（MQTT 5.0 対応）を使用。`CallbackAPIVersion.VERSION2` に統一。

### 4.1 `src/auto_cell/gateway/mqtt_client.py`

```python
"""paho-mqtt v2 ベースの publisher/subscriber。"""

import json
import logging
from collections.abc import Callable
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes

logger = logging.getLogger(__name__)


class MqttClient:
    """物理-AI core 向け MQTT クライアント（MQTT 5.0 固定）。"""

    def __init__(
        self,
        client_id: str,
        broker: str,
        port: int = 1883,
        *,
        username: str | None = None,
        password: str | None = None,
        protocol: mqtt.MQTTProtocolVersion = mqtt.MQTTProtocolVersion.MQTTv5,
    ) -> None:
        self.client_id = client_id
        self.broker = broker
        self.port = port
        self._callbacks: dict[str, Callable[[str, dict[str, Any], Properties], None]] = {}

        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            protocol=protocol,
        )
        if username:
            self._client.username_pw_set(username, password)

        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

    # ------------------------------------------------------------------
    # callbacks
    # ------------------------------------------------------------------
    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        connect_flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: Properties | None,
    ) -> None:
        logger.info("[%s] connected: %s", self.client_id, reason_code)
        for topic in list(self._callbacks.keys()):
            self._client.subscribe(topic, qos=1)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        disconnect_flags: mqtt.DisconnectFlags,
        rc: mqtt.ReasonCode,
        properties: Properties | None,
    ) -> None:
        logger.warning("[%s] disconnected: rc=%s", self.client_id, rc)

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        msg: mqtt.MQTTMessage,
    ) -> None:
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            payload = {"raw": msg.payload.decode("utf-8", errors="replace")}

        handler = self._callbacks.get(msg.topic)
        if handler:
            handler(msg.topic, payload, msg.properties)
        else:
            logger.debug("[%s] no handler for %s", self.client_id, msg.topic)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def connect(self, keepalive: int = 60) -> None:
        self._client.connect(self.broker, self.port, keepalive)
        self._client.loop_start()

    def disconnect(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        *,
        qos: int = 1,
        retain: bool = False,
        properties: Properties | None = None,
    ) -> mqtt.MQTTMessageInfo:
        data = json.dumps(payload, default=str, ensure_ascii=False).encode("utf-8")
        info = self._client.publish(topic, data, qos=qos, retain=retain, properties=properties)
        info.wait_for_publish(timeout=5.0)
        return info

    def subscribe(
        self,
        topic: str,
        callback: Callable[[str, dict[str, Any], Properties], None],
        *,
        qos: int = 1,
    ) -> None:
        """topic はリテラル or ワイルドカード（例: cell/+/cmd/bio_01/+）。"""
        self._callbacks[topic] = callback
        self._client.subscribe(topic, qos=qos)

    def is_connected(self) -> bool:
        return self._client.is_connected()
```

### 4.2 QoS / 保持 / クリーンセッション方針

- QoS: 全 topic で `1`（at least once）。冪等性ロジックで重複を吸収するため QoS2 は不要。
- retain: **telemetry/state のみ** retain。HMI/ブレインが subscribe した瞬間に最新値を取得可能。
- `cmd/ack/event/notify` は retain=false。古いコマンドが再接続時に再実行されるのを防ぐ。
- MQTT 5.0 `Session Expiry Interval` は未使用（クリーンセッション相当）。ブローカー未起動時の挙動は §11 で記載。

---

## 5. request-response パターン

### 5.1 非同期ラッパ `src/auto_cell/gateway/request_response.py`

```python
"""MQTT 5.0 Response Topic + Correlation Data を使った request-response。"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from .mqtt_client import MqttClient
from .idempotency import IdempotencyStore
from .correlation import generate_correlation_id, generate_request_id, now_iso


class MqttCommandPayload(BaseModel):
    args: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str
    request_id: str
    timestamp: str
    source: str = "brain"
    response_topic: str | None = None
    message_expiry_interval: int | None = None  # seconds


class MqttAckPayload(BaseModel):
    status: str  # accepted, completed, failed, replayed, timeout
    correlation_id: str
    request_id: str
    timestamp: str
    source: str = "gateway"
    result: dict[str, Any] | None = None


class RequestResponseClient(MqttClient):
    """cmd を publish し、ack topic で同じ Correlation Data が返ってくるまで待つ。"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._pending: dict[str, asyncio.Future[MqttAckPayload]] = {}
        self._idempotency = IdempotencyStore(ttl_seconds=86400)

    async def request(
        self,
        cu: str,
        device_id: str,
        function_id: str,
        args: dict[str, Any],
        *,
        timeout: float = 10.0,
        request_id: str | None = None,
        expiry_interval: int | None = 60,
    ) -> MqttAckPayload:
        """非同期 request-response。"""
        request_id = request_id or generate_request_id()
        correlation_id = generate_correlation_id()
        response_topic = f"cell/{cu}/ack/{device_id}/{function_id}"
        cmd_topic = f"cell/{cu}/cmd/{device_id}/{function_id}"

        payload = MqttCommandPayload(
            args=args,
            correlation_id=correlation_id,
            request_id=request_id,
            timestamp=now_iso(),
            response_topic=response_topic,
            message_expiry_interval=expiry_interval,
        )

        # MQTT 5.0 properties
        from paho.mqtt.properties import Properties
        from paho.mqtt.packettypes import PacketTypes

        props = Properties(PacketTypes.PUBLISH)
        props.ResponseTopic = response_topic
        props.CorrelationData = correlation_id.encode("utf-8")
        if expiry_interval:
            props.MessageExpiryInterval = expiry_interval

        loop = asyncio.get_event_loop()
        future: asyncio.Future[MqttAckPayload] = loop.create_future()
        self._pending[correlation_id] = future

        def on_ack(topic: str, ack: dict[str, Any], properties: Properties) -> None:
            corr = ""
            if hasattr(properties, "CorrelationData") and properties.CorrelationData:
                corr = properties.CorrelationData.decode("utf-8")
            if corr != correlation_id:
                return
            try:
                ack_payload = MqttAckPayload(**ack)
            except Exception as exc:
                ack_payload = MqttAckPayload(
                    status="failed",
                    correlation_id=corr,
                    request_id=request_id,
                    timestamp=now_iso(),
                    source="gateway",
                    result={"error": str(exc)},
                )
            if not future.done():
                future.set_result(ack_payload)

        self.subscribe(response_topic, on_ack, qos=1)
        self.publish(cmd_topic, payload.model_dump(), qos=1, properties=props)

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return MqttAckPayload(
                status="timeout",
                correlation_id=correlation_id,
                request_id=request_id,
                timestamp=now_iso(),
                source="gateway",
                result={"error": f"timeout after {timeout}s"},
            )
        finally:
            self._pending.pop(correlation_id, None)

    def request_sync(
        self,
        cu: str,
        device_id: str,
        function_id: str,
        args: dict[str, Any],
        *,
        timeout: float = 10.0,
        **kwargs: Any,
    ) -> MqttAckPayload:
        """同期ラッパ。Phase 1 初期はこちらを優先して実装する。"""
        return asyncio.run(
            self.request(cu, device_id, function_id, args, timeout=timeout, **kwargs)
        )
```

### 5.2 同期ラッパの利用場面

- **Phase 1 初期**: L1 サイクル実行器は同期 `request_sync` で実装。非同期はテスト・HMI 経由の並列承認処理で後から置き換える。
- **非同期必須ケース**: 複数デバイスへの並列 cmd、承認待ち中の他タスク継続。

---

## 6. correlation_id 管理

`correlation_id` は cmd/ack/approval/event_store を横断するトレーサビリティ用 ID。`request_id` は 1 回のコマンド/承認単位の冪等キー。

### 6.1 `src/auto_cell/gateway/correlation.py`

```python
"""correlation_id / request_id 生成。UUIDv7/ULID を推奨。"""

import uuid
from datetime import datetime, timezone


def generate_correlation_id() -> str:
    """cmd/ack/approval/event_store を紐付ける横断 ID。"""
    return f"c_{uuid.uuid4().hex}"


def generate_request_id() -> str:
    """1 コマンド・1 承認要求の冪等キー。"""
    return f"req_{uuid.uuid4().hex}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
```

### 6.2 紐付けルール

| 用途 | ID | 保存先 |
|---|---|---|
| cmd 発行 | `correlation_id` + `request_id` | `event_store` command テーブル |
| ack 受信 | 同じ `correlation_id` + `request_id` | command テーブル更新 |
| 承認要求 | `request_id` = approval topic suffix、`correlation_id` = cmd と同じ | `state/approval/{request_id}` + event_store |
| 承認応答（HMI） | `request_id` でマッチ | `state/approval/{request_id}` 更新 |
| 実行完了 event | `correlation_id` でマッチ | `event_store` event テーブル |

---

## 7. 冪等性実装

### 7.1 `src/auto_cell/gateway/idempotency.py`

```python
"""request_id による重複実行防止。"""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class IdempotencyRecord:
    request_id: str
    status: str
    result: dict[str, Any] | None = None
    expires_at: float = 0.0


class IdempotencyStore:
    """
    受信側（gateway/virtual_edge）が同一 request_id の重複実行を防ぐ。
    TTL は Message Expiry Interval より長く（デフォルト 24h）。
    """

    def __init__(self, ttl_seconds: float = 86400) -> None:
        self.ttl_seconds = ttl_seconds
        self._records: dict[str, IdempotencyRecord] = {}

    def _now(self) -> float:
        return time.time()

    def is_known(self, request_id: str) -> bool:
        rec = self._records.get(request_id)
        if rec is None:
            return False
        if rec.expires_at < self._now():
            del self._records[request_id]
            return False
        return True

    def get(self, request_id: str) -> IdempotencyRecord | None:
        if self.is_known(request_id):
            return self._records[request_id]
        return None

    def save(
        self,
        request_id: str,
        status: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        self._records[request_id] = IdempotencyRecord(
            request_id=request_id,
            status=status,
            result=result,
            expires_at=self._now() + self.ttl_seconds,
        )

    def cleanup(self) -> None:
        now = self._now()
        expired = [rid for rid, rec in self._records.items() if rec.expires_at < now]
        for rid in expired:
            del self._records[rid]
```

### 7.2 受信側の重複判定フロー

```python
def _on_cmd(self, topic: str, payload: dict, properties: Properties) -> None:
    request_id = payload.get("request_id", "")
    correlation_id = payload.get("correlation_id", request_id)
    function_id = topic.split("/")[-1]

    # 1. 冪等チェック
    if self.idempotency.is_known(request_id):
        cached = self.idempotency.get(request_id)
        self._ack(function_id, "replayed", cached.result, correlation_id, request_id)
        return

    # 2. Message Expiry Interval 超過チェック（broker でも弾かれるが二重チェック）
    sent = payload.get("timestamp")
    expiry = payload.get("message_expiry_interval")
    if sent and expiry and _seconds_since(sent) > expiry:
        self._ack(function_id, "failed", {"error": "expired"}, correlation_id, request_id)
        return

    # 3. 実行
    status, result = self._execute(function_id, payload.get("args", {}))
    self.idempotency.save(request_id, status, result)
    self._ack(function_id, status, result, correlation_id, request_id)
```

### 7.3 Message Expiry Interval

- ブローカーが未配送メッセージを破棄する TTL。
- 推奨: cmd=60s、program=300s、approval 要求=タイムアウト値（10min/30min）と同値。
- 受信側でも二重チェックし、NTP 未同期時の安全側動作を担保。

---

## 8. `infra/virtual_edge/dummy_bioreactor.py`

MQTT 経由で `plant_model.step()` を呼び出す仮想バイオリアクター。実機前の結線検証・CI 閉ループ run に使用。

```python
"""MQTT 仮想バイオリアクター（plant_model を backend とする virtual_edge）。"""

import argparse
import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes

from auto_cell.gateway.mqtt_client import MqttClient
from auto_cell.gateway.idempotency import IdempotencyStore
from auto_cell.gateway.correlation import now_iso

# sim/plant_model を PYTHONPATH 経由で import（repo ルートを venv path に含める）
from sim.plant_model import PlantModel, Actuators

logger = logging.getLogger(__name__)


class DummyBioreactorEdge(MqttClient):
    """
    - ブレインからの cmd を受けてアクチュエータを更新
    - 一定周期で plant_model.step() を実行し telemetry を publish
    - request_id 重複は replay ack を返す
    """

    def __init__(
        self,
        culture_unit_id: str,
        *,
        device_id: str = "bioreactor_01",
        broker: str = "localhost",
        port: int = 1883,
        cycle_interval_s: float = 30.0,
    ) -> None:
        client_id = f"ve_{culture_unit_id}_{device_id}"
        super().__init__(client_id, broker, port)
        self.cu = culture_unit_id
        self.device_id = device_id
        self.cycle_interval_s = cycle_interval_s

        self.actuators = Actuators(
            perfusion_rate_vvd=0.0,
            agitation_rpm=80.0,
            do_setpoint=40.0,
            ph_setpoint=7.1,
            feed_glucose=0.0,
            feed_glutamine=0.0,
        )
        self.latest_sensors: dict[str, Any] = {}
        self.idempotency = IdempotencyStore(ttl_seconds=86400)
        self._plant = PlantModel()

    def start(self) -> None:
        self.connect()
        # cmd wildcard: cell/{cu}/cmd/{device_id}/+
        self.subscribe(
            f"cell/{self.cu}/cmd/{self.device_id}/+",
            self._on_cmd,
            qos=1,
        )
        # program wildcard
        self.subscribe(
            f"cell/{self.cu}/program/{self.device_id}/request",
            self._on_program_request,
            qos=1,
        )
        self.publish(
            f"cell/{self.cu}/state/device/{self.device_id}",
            {"status": "ONLINE", "device_id": self.device_id, "ts": now_iso()},
            retain=True,
        )

    # ------------------------------------------------------------------
    # command handling
    # ------------------------------------------------------------------
    def _on_cmd(self, topic: str, payload: dict[str, Any], properties: Properties) -> None:
        function_id = topic.split("/")[-1]
        request_id = payload.get("request_id", "unknown")
        correlation_id = payload.get("correlation_id", request_id)

        if self.idempotency.is_known(request_id):
            cached = self.idempotency.get(request_id)
            self._ack(function_id, "replayed", cached.result if cached else None,
                      correlation_id, request_id)
            return

        status, result = self._execute(function_id, payload.get("args", {}))
        self.idempotency.save(request_id, status, result)
        self._ack(function_id, status, result, correlation_id, request_id)

    def _execute(self, function_id: str, args: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
        try:
            if function_id == "set_perfusion_rate":
                self.actuators.perfusion_rate_vvd = float(args["vvd"])
            elif function_id == "set_agitation_rpm":
                self.actuators.agitation_rpm = float(args["rpm"])
            elif function_id == "set_gas_setpoint":
                # args: {"do_percent": 40.0} or {"ph_setpoint": 7.1}
                if "do_percent" in args:
                    self.actuators.do_setpoint = float(args["do_percent"])
                if "ph_setpoint" in args:
                    self.actuators.ph_setpoint = float(args["ph_setpoint"])
            elif function_id == "feed":
                self.actuators.feed_glucose += float(args.get("glucose_g_l", 0.0))
                self.actuators.feed_glutamine += float(args.get("glutamine_mmol_l", 0.0))
            elif function_id == "exchange_media":
                # plant_model.step 内で perfusion_rate_vvd に応じて培地交換を計算
                pass
            elif function_id == "trigger_passage":
                self.actuators.perfusion_rate_vvd = 0.0
                self._plant.reset_after_passage()
            elif function_id == "take_sample":
                return "completed", {"sensors": self.latest_sensors.copy()}
            else:
                return "failed", {"error": f"unknown function: {function_id}"}
            return "accepted", {"actuators": self.actuators.model_dump()}
        except Exception as exc:
            return "failed", {"error": str(exc)}

    def _ack(
        self,
        function_id: str,
        status: str,
        result: dict[str, Any] | None,
        correlation_id: str,
        request_id: str,
    ) -> None:
        topic = f"cell/{self.cu}/ack/{self.device_id}/{function_id}"
        ack = {
            "status": status,
            "result": result,
            "correlation_id": correlation_id,
            "request_id": request_id,
            "timestamp": now_iso(),
            "source": self.device_id,
        }
        props = Properties(PacketTypes.PUBLISH)
        props.CorrelationData = correlation_id.encode("utf-8")
        self.publish(topic, ack, qos=1, properties=props)

    # ------------------------------------------------------------------
    # program handling
    # ------------------------------------------------------------------
    def _on_program_request(self, topic: str, payload: dict[str, Any], properties: Properties) -> None:
        request_id = payload.get("request_id", "unknown")
        correlation_id = payload.get("correlation_id", request_id)
        # v1: program 実行は stub。将来 LADS Program/Result 対応。
        result = {"status": "program_stub_executed", "program_id": payload.get("program_id")}
        self.publish(
            f"cell/{self.cu}/program/{self.device_id}/response",
            {
                "status": "completed",
                "result": result,
                "correlation_id": correlation_id,
                "request_id": request_id,
                "timestamp": now_iso(),
                "source": self.device_id,
            },
            qos=1,
        )

    # ------------------------------------------------------------------
    # main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        self.start()
        try:
            while True:
                dt_days = self.cycle_interval_s / 86400.0
                self.latest_sensors = self._plant.step(self.actuators, dt=dt_days)

                telemetry = {
                    "timestamp": now_iso(),
                    "device_id": self.device_id,
                    "actuators": self.actuators.model_dump(),
                    "values": self.latest_sensors,
                }
                self.publish(
                    f"cell/{self.cu}/telemetry/{self.device_id}/all",
                    telemetry,
                    qos=1,
                    retain=True,
                )

                # 個別 telemetry（HMI/ルールエンジンが subscribe しやすい）
                for key, value in self.latest_sensors.items():
                    self.publish(
                        f"cell/{self.cu}/telemetry/{self.device_id}/{key}",
                        {
                            "timestamp": now_iso(),
                            "value": value,
                            "unit": self._guess_unit(key),
                            "quality": "GOOD",
                            "source": self.device_id,
                        },
                        qos=1,
                        retain=True,
                    )

                time.sleep(self.cycle_interval_s)
        finally:
            self.disconnect()

    @staticmethod
    def _guess_unit(key: str) -> str:
        unit_map = {
            "vcd": "cells/mL",
            "viability": "ratio",
            "glucose": "mM",
            "lactate": "mM",
            "glutamine": "mM",
            "osmolality": "mOsm/kg",
            "aggregate_diameter_um": "um",
            "do_percent": "percent",
            "ph": "pH",
            "temp_c": "C",
        }
        return unit_map.get(key, "")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cu", default="cu_001")
    parser.add_argument("--device", default="bioreactor_01")
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--interval", type=float, default=30.0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    edge = DummyBioreactorEdge(
        culture_unit_id=args.cu,
        device_id=args.device,
        broker=args.broker,
        port=args.port,
        cycle_interval_s=args.interval,
    )
    edge.run()


if __name__ == "__main__":
    main()
```

### 8.1 想定 `sim/plant_model` IF

```python
from pydantic import BaseModel


class Actuators(BaseModel):
    perfusion_rate_vvd: float
    agitation_rpm: float
    do_setpoint: float
    ph_setpoint: float
    feed_glucose: float
    feed_glutamine: float


class PlantModel:
    def step(self, actuators: Actuators, *, dt: float) -> dict:
        ...

    def reset_after_passage(self) -> None:
        ...
```

`sim/plant_model/__init__.py` は既に `step(actuators) -> sensors` として設計されている（docstring）。上記 `Actuators` dataclass を追加するか、既存実装に合わせて adapter を書く。

---

## 9. LADS / OPC-UA クライアント骨格

`kg_to_auto_cell.md` §7.1 により、バイオリアクタ本体は **OPC-UA + LADS 第一**。`gateway/` 配下に抽象を置き、実機差替を閉じる。

### 9.1 `src/auto_cell/gateway/lads_opcua_client.py`

```python
"""LADS Functional Unit / Function 抽象 + OPC-UA 接続骨格。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from collections.abc import Callable
from typing import Any


class FunctionType(str, Enum):
    SENSOR = "sensor"          # analog sensor → telemetry
    CONTROLLER = "controller"  # setpoint controller → cmd/ack
    ACTUATOR = "actuator"      # pump/motor → cmd/ack
    PROGRAM = "program"        # LADS Program/Result → program topic


@dataclass(frozen=True)
class LadsFunction:
    function_id: str           # e.g. "Temperature", "pH", "PerfusionRate"
    display_name: str
    function_type: FunctionType
    node_id: str               # OPC-UA node id (ns=2;i=...)
    unit: str | None = None
    min_value: float | None = None
    max_value: float | None = None


class LadsFunctionalUnit(ABC):
    """LADS Functional Unit（槽＝1台のバイオリアクター）抽象。"""

    def __init__(self, unit_id: str, functions: list[LadsFunction]) -> None:
        self.unit_id = unit_id
        self.functions: dict[str, LadsFunction] = {f.function_id: f for f in functions}

    @abstractmethod
    async def connect(self) -> None:
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        ...

    @abstractmethod
    async def subscribe(
        self,
        function_id: str,
        callback: Callable[[str, Any], None],
    ) -> None:
        """sensor Function の値変化を subscribe。"""
        ...

    @abstractmethod
    async def call_method(
        self,
        function_id: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        """controller/actuator Function の method 呼び出し。"""
        ...

    @abstractmethod
    async def read(self, function_id: str) -> Any:
        """1 回限りの読み取り。"""
        ...


class OpcUaLadsClient(LadsFunctionalUnit):
    """
    asyncua を使った LADS/OPC-UA 接続骨格。
    Phase 1 では stub 実装。Phase 2 で asyncua 接続を完成させる。
    """

    def __init__(
        self,
        unit_id: str,
        functions: list[LadsFunction],
        opcua_url: str,
        namespace_index: int = 2,
    ) -> None:
        super().__init__(unit_id, functions)
        self.opcua_url = opcua_url
        self.namespace_index = namespace_index
        self._client: Any = None

    async def connect(self) -> None:
        from asyncua import Client  # type: ignore[import-untyped]
        self._client = Client(self.opcua_url)
        await self._client.connect()

    async def disconnect(self) -> None:
        if self._client:
            await self._client.disconnect()

    async def subscribe(
        self,
        function_id: str,
        callback: Callable[[str, Any], None],
    ) -> None:
        fn = self.functions[function_id]
        node = self._client.get_node(fn.node_id)
        handler = _OpcUaDataChangeHandler(callback)
        sub = await self._client.create_subscription(500, handler)
        await sub.subscribe_data_change(node)

    async def call_method(self, function_id: str, args: dict[str, Any]) -> dict[str, Any]:
        fn = self.functions[function_id]
        node = self._client.get_node(fn.node_id)
        return await node.call_method(f"{fn.node_id}:{function_id}", *args.values())

    async def read(self, function_id: str) -> Any:
        fn = self.functions[function_id]
        node = self._client.get_node(fn.node_id)
        return await node.read_value()


class _OpcUaDataChangeHandler:
    def __init__(self, callback: Callable[[str, Any], None]) -> None:
        self.callback = callback

    def datachange_notification(self, node, val, data) -> None:  # type: ignore[no-untyped-def]
        self.callback(str(node), val)
```

### 9.2 LADS → MQTT マッピング

| LADS 概念 | MQTT topic | 備考 |
|---|---|---|
| Functional Unit | `device_id` | 1 槽 = 1 device |
| sensor Function | `telemetry/{device_id}/{function_id}` | subscribe → publish retain |
| controller/actuator method | `cmd/{device_id}/{function_id}` + `ack/...` | method 呼び出しを cmd/ack で表現 |
| Program/Result | `program/{device_id}/request` + `program/{device_id}/response` | レシピアップロード・結果取得 |
| LADS alarm | `event/{device_id}/{alarm_code}` | severity 付き |

---

## 10. SiLA2 クライアント骨格

`kg_to_auto_cell.md` §7.1 により、サンプリングロボ・分注・at-line 分析器は SiLA2 従。

### 10.1 `src/auto_cell/gateway/sila_client.py`

```python
"""SiLA2 Feature 抽象 + クライアント骨格。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Any


@dataclass(frozen=True)
class SiLAMethod:
    name: str
    parameter_schema: dict[str, Any]
    response_schema: dict[str, Any]


@dataclass(frozen=True)
class SiLAFeature:
    feature_id: str
    display_name: str
    commands: dict[str, SiLAMethod] = field(default_factory=dict)
    properties: dict[str, SiLAMethod] = field(default_factory=dict)
    observations: dict[str, SiLAMethod] = field(default_factory=dict)


class SiLA2Client(ABC):
    """
    SiLA2 周辺機器向け抽象クライアント。
    Phase 1 では interface のみ。実装は Phase 2 で sila2lib 等を導入。
    """

    def __init__(self, server_uri: str, features: list[SiLAFeature]) -> None:
        self.server_uri = server_uri
        self.features: dict[str, SiLAFeature] = {f.feature_id: f for f in features}

    @abstractmethod
    async def connect(self) -> None:
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        ...

    @abstractmethod
    async def call_command(
        self,
        feature_id: str,
        command_id: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        ...

    @abstractmethod
    async def subscribe_property(
        self,
        feature_id: str,
        property_id: str,
        callback: Callable[[Any], None],
    ) -> None:
        ...

    @abstractmethod
    async def observe_event(
        self,
        feature_id: str,
        event_id: str,
        callback: Callable[[Any], None],
    ) -> None:
        ...
```

### 10.2 SiLA2 → MQTT マッピング

| SiLA2 概念 | MQTT topic | 備考 |
|---|---|---|
| Feature | `device_id` 相当 | e.g. "sampler_robot_01" |
| Property | `telemetry/{device_id}/{property_id}` | 定期/変化時 publish |
| Command | `cmd/{device_id}/{command_id}` + `ack/...` | 命令実行 |
| Event/Observable | `event/{device_id}/{event_id}` | 状態遷移通知 |

---

## 11. テスト計画

### 11.1 テストファイル一覧

| ファイル | 内容 |
|---|---|
| `tests/test_mqtt_client.py` | 接続/購読/発行の基本動作 |
| `tests/test_mqtt_idempotency.py` | 重複 request_id → replay ack、TTL 超過 → 新規実行 |
| `tests/test_virtual_edge.py` | dummy_bioreactor 起動 → cmd → telemetry/ack 検証 |
| `tests/test_request_response.py` | Response Topic + Correlation Data 紐付け、タイムアウト |

### 11.2 `tests/conftest.py`（amqtt 埋め込みブローカー）

```python
"""MQTT テスト用の埋め込みブローカー fixture。"""

import asyncio
import pytest
import pytest_asyncio

from amqtt.broker import Broker  # type: ignore[import-untyped]
from amqtt.client import MQTTClient  # type: ignore[import-untyped]


@pytest_asyncio.fixture(scope="session")
async def mqtt_broker():
    config = {
        "listeners": {
            "default": {
                "type": "tcp",
                "bind": "127.0.0.1",
                "port": 1883,
            }
        },
        "sys_interval": 0,
        "auth": {"allow-anonymous": True},
    }
    broker = Broker(config)
    await broker.start()
    yield broker
    await broker.shutdown()


@pytest.fixture
def broker_host():
    return "127.0.0.1"
```

> CI では `amqtt` を dev 依存に加えるか、GitHub Actions service container で `eclipse-mosquitto` を起動する。

### 11.3 冪等性テスト例 `tests/test_mqtt_idempotency.py`

```python
"""MQTT 冪等性テスト。"""

import asyncio
import pytest

from auto_cell.gateway.request_response import RequestResponseClient
from infra.virtual_edge.dummy_bioreactor import DummyBioreactorEdge


@pytest.mark.asyncio
async def test_duplicate_command_returns_replayed(mqtt_broker, broker_host):
    edge = DummyBioreactorEdge(
        "cu_test", device_id="bio_test", broker=broker_host,
        port=1883, cycle_interval_s=3600,  # telemetry は周期長め
    )
    edge.start()

    brain = RequestResponseClient("brain_test", broker_host, 1883)
    brain.connect()
    await asyncio.sleep(0.3)

    req_id = "req_duplicate_001"
    ack1 = await brain.request(
        "cu_test", "bio_test", "set_perfusion_rate",
        {"vvd": 2.0}, request_id=req_id, timeout=5.0,
    )
    assert ack1.status in ("accepted", "completed")

    ack2 = await brain.request(
        "cu_test", "bio_test", "set_perfusion_rate",
        {"vvd": 999.0}, request_id=req_id, timeout=5.0,
    )
    assert ack2.status == "replayed"
    # 2 回目の引数は無視され、1 回目の結果が返る
    assert ack2.result["actuators"]["perfusion_rate_vvd"] == 2.0

    edge.disconnect()
    brain.disconnect()
```

### 11.4 virtual_edge 統合テスト例 `tests/test_virtual_edge.py`

```python
"""virtual_edge + plant_model 統合テスト。"""

import asyncio
import pytest

from auto_cell.gateway.request_response import RequestResponseClient
from infra.virtual_edge.dummy_bioreactor import DummyBioreactorEdge


@pytest.mark.asyncio
async def test_set_perfusion_rate_changes_telemetry(mqtt_broker, broker_host):
    edge = DummyBioreactorEdge(
        "cu_integ", device_id="bio_01", broker=broker_host,
        port=1883, cycle_interval_s=1.0,
    )
    edge.start()

    brain = RequestResponseClient("brain_integ", broker_host, 1883)
    brain.connect()
    await asyncio.sleep(0.3)

    ack = await brain.request(
        "cu_integ", "bio_01", "set_perfusion_rate", {"vvd": 3.0}, timeout=5.0,
    )
    assert ack.status == "accepted"

    # telemetry/all の retain を受け取る
    received = {}

    def on_telemetry(topic, payload, properties):
        received.update(payload)

    brain.subscribe(
        "cell/cu_integ/telemetry/bio_01/all", on_telemetry, qos=1,
    )
    await asyncio.sleep(1.5)

    assert "values" in received
    assert "vcd" in received["values"]

    edge.disconnect()
    brain.disconnect()
```

---

## 12. 依存関係

### 12.1 `pyproject.toml` 更新

```toml
[project]
dependencies = [
    "physical-ai-core",
    "scipy>=1.11",
    "numpy>=1.26",
    "paho-mqtt>=2.1",      # MQTT 5.0 Response Topic / Correlation Data
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-asyncio>=0.23",
    "amqtt>=0.11",         # テスト用埋め込み MQTT broker
    "ruff",
    "mypy",
]
gateway = [
    "asyncua>=1.0",        # LADS/OPC-UA 接続（Phase 1 骨格、Phase 2 本格）
]
```

### 12.2 追加対応

- `uv sync --extra dev` 後に `pytest tests/test_mqtt_*.py` を実行。
- `ruff`/`mypy` に `src/auto_cell/gateway/`、`infra/virtual_edge/` を含める（既存 `ruff.toml` が `src` を対象にしていれば追加不要）。
- `sim/plant_model` が `src` 外にあるため、テスト実行時は `PYTHONPATH=. pytest ...` とするか、`pyproject.toml` に `tool.pytest.ini_options.pythonpath = ["."]` を追加。

---

## 13. リスクと対応

| # | リスク | 影響 | 対応 |
|---|---|---|---|
| 1 | **非同期 request-response の複雑性** | デッドロック・タイムアウト漏れ | まず同期 `request_sync` を実装。非同期は単体テスト後に段階導入 |
| 2 | **ブローカー未起動時の挙動** | テスト/CI 失敗、起動順序依存 | `connect()` は指定期間リトライ（`tenacity` 推奨）。未接続時は cmd を queue せず即座 `timeout` ack。HMI には `state/device/{device_id}` が OFFLINE になるよう通知 |
| 3 | **`Correlation Data` のエンコーディング違い** | cmd/ack 紐付け失敗 | UTF-8 固定。受信側は bytes→str→比較を厳密に行う |
| 4 | **request_id 衝突/欠落** | 重複実行またはログ不整合 | 空文字の request_id は拒否。UUIDv4/v7 生成を gateway/ブレイン両方で共通化 |
| 5 | **冪等 store のメモリリーク** | 長時間 run でメモリ圧迫 | TTL 付き dict + 定期 cleanup（毎 1h）。Phase 2 では SQLite/Redis 置き換え |
| 6 | **LADS/SiLA2 SDK 未導入** | Phase 1 実機接続不可 | 抽象骨格のみ実装し、virtual_edge で閉ループを先に成立させる |
| 7 | **paho-mqtt v1/v2 API 違い** | 型エラー・実行時エラー | `paho-mqtt>=2.1` 固定、`CallbackAPIVersion.VERSION2` 必須 |

---

## 14. 実装工数見積もり

`05_implementation_plan_phase1.md` Sprint 6（Week 6）を想定。LADS/SiLA2 骨格込みで **2 週間**を見込む。

| 週 | タスク | 工数 | 成果物 |
|---|---|---|---|
| Week 6-1 | MQTT topic 契約 YAML、Pydantic payload、`mqtt_client.py` | 3 d | `config/mqtt_topics.yaml`, `mqtt_client.py` |
| Week 6-2 | request-response、correlation_id、冪等性実装 + 単体テスト | 3 d | `request_response.py`, `correlation.py`, `idempotency.py`, `tests/test_mqtt_*.py` |
| Week 6-3 | `dummy_bioreactor.py` + `plant_model` 接続 + virtual_edge 統合テスト | 3 d | `infra/virtual_edge/dummy_bioreactor.py`, `tests/test_virtual_edge.py` |
| Week 6-4 | LADS/OPC-UA 骨格、SiLA2 骨格、device_profile stub | 2 d | `lads_opcua_client.py`, `sila_client.py`, `device_profile.py` |
| Week 7-1 | レビュー・CI 整備・ドキュメント更新 | 1 d | 本計画書更新、CI pass |
| **合計** | | **~12 日（2 週間）** | |

**並列可能タスク**:
- HMI/承認フロー（Sprint 7）と並行して `state/approval/{request_id}` の E2E を Week 7 で結合。
- LADS/SiLA2 骨格は virtual_edge 成立後に実装可能（クリティカルパスから外しても可）。

---

## 15. 参照

- `docs/design/closed_loop_planning/05_implementation_plan_phase1.md`
- `docs/design/closed_loop_planning/06_critical_path_and_work_order.md`
- `docs/design/closed_loop_planning/03_swarm_findings_integration.md`
- `docs/design/closed_loop_planning/02_missing_assets_for_closed_loop.md`
- `docs/design/kg_to_auto_cell.md` §7.1 / §7.3
- `docs/design/adr/0001-control-architecture.md`
- `sim/plant_model/__init__.py`
