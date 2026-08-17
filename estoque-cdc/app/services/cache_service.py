from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import redis

from app.config.settings import settings


@dataclass(frozen=True)
class AppliedEvent:
    table: str
    operation: str | None
    record_id: int | None
    medicamento_id: int | None
    stock: int | None


class CacheService:
    MEDICAMENTOS_KEY = "cdc:medicamentos"
    LOTES_KEY = "cdc:lotes"
    MOVIMENTACOES_KEY = "cdc:movimentacoes"
    MOVIMENTACOES_TIMELINE_KEY = "cdc:movimentacoes:timeline"
    ALERTAS_KEY = "cdc:alertas"
    METRICS_KEY = "cdc:metricas"

    def __init__(self) -> None:
        self.client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
        )
        self.client.ping()

    @staticmethod
    def _dumps(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, default=str)

    @staticmethod
    def _loads(payload: str | None) -> dict[str, Any] | None:
        if not payload:
            return None
        value = json.loads(payload)
        return value if isinstance(value, dict) else None

    @staticmethod
    def _as_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        return int(value)

    def apply_event(self, table: str, event: dict[str, Any]) -> AppliedEvent:
        operation = event.get("op")
        before = event.get("before")
        after = event.get("after")
        row = after or before

        if not isinstance(row, dict) or "id" not in row:
            return AppliedEvent(table, operation, None, None, None)

        record_id = int(row["id"])
        medicamento_id: int | None = None
        stock: int | None = None

        if table == "medicamentos":
            self._apply_hash_entity(
                self.MEDICAMENTOS_KEY,
                record_id,
                after,
            )
            medicamento_id = record_id

        elif table == "lotes":
            old_med_id = self._as_int(
                before.get("medicamento_id") if isinstance(before, dict) else None
            )
            new_med_id = self._as_int(
                after.get("medicamento_id") if isinstance(after, dict) else None
            )
            self._apply_hash_entity(self.LOTES_KEY, record_id, after)
            medicamento_id = new_med_id or old_med_id

            affected = {mid for mid in (old_med_id, new_med_id) if mid is not None}
            for mid in affected:
                current = self.recompute_stock(mid)
                if mid == medicamento_id:
                    stock = current

        elif table == "movimentacoes":
            lote_id = self._as_int(row.get("lote_id"))
            medicamento_id = self.medication_id_for_lot(lote_id)
            enriched = dict(after or row)
            enriched["medicamento_id"] = medicamento_id
            enriched["cdc_operacao"] = operation
            enriched["cdc_ts_ms"] = event.get("ts_ms")

            if after is None:
                self.client.hdel(self.MOVIMENTACOES_KEY, record_id)
                self.client.zrem(self.MOVIMENTACOES_TIMELINE_KEY, record_id)
            else:
                score = self._movement_score(enriched, event)
                pipeline = self.client.pipeline(transaction=True)
                pipeline.hset(
                    self.MOVIMENTACOES_KEY,
                    record_id,
                    self._dumps(enriched),
                )
                pipeline.zadd(
                    self.MOVIMENTACOES_TIMELINE_KEY,
                    {str(record_id): score},
                )
                pipeline.hincrby(self.METRICS_KEY, "eventos_processados", 1)
                pipeline.hset(self.METRICS_KEY, "ultimo_evento_epoch", time.time())
                pipeline.execute()
                self._trim_movement_history()

            if medicamento_id is not None:
                stock = self.current_stock(medicamento_id)

        return AppliedEvent(
            table=table,
            operation=operation,
            record_id=record_id,
            medicamento_id=medicamento_id,
            stock=stock,
        )

    def _apply_hash_entity(
        self,
        key: str,
        record_id: int,
        payload: dict[str, Any] | None,
    ) -> None:
        if payload is None:
            self.client.hdel(key, record_id)
            return
        self.client.hset(key, record_id, self._dumps(payload))

    @staticmethod
    def _movement_score(
        row: dict[str, Any],
        event: dict[str, Any],
    ) -> float:
        ts_ms = event.get("ts_ms")
        if isinstance(ts_ms, (int, float)):
            return float(ts_ms)
        return time.time() * 1000

    def _trim_movement_history(self) -> None:
        total = self.client.zcard(self.MOVIMENTACOES_TIMELINE_KEY)
        excess = total - settings.movement_history_limit
        if excess <= 0:
            return
        old_ids = self.client.zrange(
            self.MOVIMENTACOES_TIMELINE_KEY,
            0,
            excess - 1,
        )
        if not old_ids:
            return
        pipeline = self.client.pipeline(transaction=True)
        pipeline.zrem(self.MOVIMENTACOES_TIMELINE_KEY, *old_ids)
        pipeline.hdel(self.MOVIMENTACOES_KEY, *old_ids)
        pipeline.execute()

    def medication_id_for_lot(self, lote_id: int | None) -> int | None:
        if lote_id is None:
            return None
        lote = self._loads(self.client.hget(self.LOTES_KEY, lote_id))
        if not lote:
            return None
        return self._as_int(lote.get("medicamento_id"))

    def recompute_stock(self, medicamento_id: int) -> int:
        total = 0
        for payload in self.client.hvals(self.LOTES_KEY):
            lote = self._loads(payload)
            if not lote:
                continue
            if self._as_int(lote.get("medicamento_id")) == medicamento_id:
                total += int(lote.get("quantidade") or 0)
        self.client.hset("cdc:estoques", medicamento_id, total)
        return total

    def current_stock(self, medicamento_id: int) -> int:
        value = self.client.hget("cdc:estoques", medicamento_id)
        if value is None:
            return self.recompute_stock(medicamento_id)
        return int(value)

    def replenishment_blocked(self, medicamento_id: int) -> bool:
        medicamento = self._loads(
            self.client.hget(self.MEDICAMENTOS_KEY, medicamento_id)
        )
        if not medicamento:
            return False
        value = medicamento.get("bloqueio_reabastecimento", False)
        return value in (True, 1, "1", "true", "True")

    def acquire_replenishment_lock(self, medicamento_id: int) -> bool:
        return bool(
            self.client.set(
                f"cdc:reabastecimento:pendente:{medicamento_id}",
                "1",
                nx=True,
                ex=settings.replenishment_cooldown_seconds,
            )
        )

    def save_alert(
        self,
        medicamento_id: int,
        requested_quantity: int,
        observed_stock: int,
    ) -> None:
        alert = {
            "medicamento_id": medicamento_id,
            "quantidade_solicitada": requested_quantity,
            "estoque_observado": observed_stock,
            "criado_em_epoch": time.time(),
        }
        pipeline = self.client.pipeline(transaction=True)
        pipeline.lpush(self.ALERTAS_KEY, self._dumps(alert))
        pipeline.ltrim(self.ALERTAS_KEY, 0, 99)
        pipeline.execute()

    def list_medications(self) -> list[dict[str, Any]]:
        return [
            item
            for item in (
                self._loads(payload)
                for payload in self.client.hvals(self.MEDICAMENTOS_KEY)
            )
            if item is not None
        ]

    def list_lots(self) -> list[dict[str, Any]]:
        return [
            item
            for item in (
                self._loads(payload)
                for payload in self.client.hvals(self.LOTES_KEY)
            )
            if item is not None
        ]

    def list_movements(self, limit: int = 100) -> list[dict[str, Any]]:
        ids = self.client.zrevrange(
            self.MOVIMENTACOES_TIMELINE_KEY,
            0,
            max(limit - 1, 0),
        )
        if not ids:
            return []
        values = self.client.hmget(self.MOVIMENTACOES_KEY, ids)
        return [
            item
            for item in (self._loads(value) for value in values)
            if item is not None
        ]

    def list_alerts(self, limit: int = 50) -> list[dict[str, Any]]:
        return [
            item
            for item in (
                self._loads(payload)
                for payload in self.client.lrange(self.ALERTAS_KEY, 0, limit - 1)
            )
            if item is not None
        ]

    def health(self) -> dict[str, Any]:
        return {
            "redis": bool(self.client.ping()),
            "medicamentos": self.client.hlen(self.MEDICAMENTOS_KEY),
            "lotes": self.client.hlen(self.LOTES_KEY),
            "movimentacoes": self.client.zcard(self.MOVIMENTACOES_TIMELINE_KEY),
            "eventos_processados": int(
                self.client.hget(self.METRICS_KEY, "eventos_processados") or 0
            ),
        }
