from __future__ import annotations
import json
from typing import Any

def parse_debezium_message(value: bytes | str | dict[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {"before": None, "after": None, "op": None, "ts_ms": None, "source": {}}
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    payload = json.loads(value) if isinstance(value, str) else value
    # Com schemas.enable=false o envelope já é o objeto raiz; com schema=true fica em payload.
    envelope = payload.get("payload", payload)
    return {
        "before": envelope.get("before"),
        "after": envelope.get("after"),
        "op": envelope.get("op"),
        "ts_ms": envelope.get("ts_ms"),
        "source": envelope.get("source", {}),
    }
