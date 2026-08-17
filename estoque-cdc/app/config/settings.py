from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


@dataclass(frozen=True)
class Settings:
    kafka_bootstrap_servers: str = _env(
        "KAFKA_BOOTSTRAP_SERVERS",
        "localhost:19090,localhost:19091,localhost:19092",
    )
    kafka_group_id: str = _env(
        "KAFKA_GROUP_ID",
        "estoque-redis-dashboard-v1",
    )
    topic_prefix: str = _env("CDC_TOPIC_PREFIX", "estoque")
    replenishment_topic: str = _env(
        "REABASTECIMENTO_TOPIC",
        "reabastecimento",
    )

    redis_host: str = _env("REDIS_HOST", "localhost")
    redis_port: int = int(_env("REDIS_PORT", "6379"))
    redis_db: int = int(_env("REDIS_DB", "0"))

    minimum_stock: int = int(_env("ESTOQUE_MINIMO", "20"))
    replenishment_quantity: int = int(
        _env("QUANTIDADE_REABASTECIMENTO", "100")
    )
    replenishment_cooldown_seconds: int = int(
        _env("REABASTECIMENTO_COOLDOWN_SEGUNDOS", "300")
    )
    dashboard_refresh_seconds: int = int(
        _env("DASHBOARD_REFRESH_SECONDS", "2")
    )
    movement_history_limit: int = int(
        _env("MOVEMENT_HISTORY_LIMIT", "500")
    )

    @property
    def kafka_servers(self) -> list[str]:
        return [
            server.strip()
            for server in self.kafka_bootstrap_servers.split(",")
            if server.strip()
        ]

    @property
    def cdc_topics(self) -> list[str]:
        return [
            f"{self.topic_prefix}.public.medicamentos",
            f"{self.topic_prefix}.public.lotes",
            f"{self.topic_prefix}.public.movimentacoes",
        ]


settings = Settings()
