from __future__ import annotations

import json
import logging
import time

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable

from app.config.settings import settings
from app.consumers.cdc_parser import parse_debezium_message
from app.services.cache_service import CacheService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


def table_from_topic(topic: str) -> str:
    return topic.rsplit(".", 1)[-1]


def create_consumer() -> KafkaConsumer:
    last_error: Exception | None = None
    for attempt in range(1, 31):
        try:
            return KafkaConsumer(
                *settings.cdc_topics,
                bootstrap_servers=settings.kafka_servers,
                group_id=settings.kafka_group_id,
                auto_offset_reset="earliest",
                enable_auto_commit=False,
                value_deserializer=lambda value: value,
                consumer_timeout_ms=-1,
                request_timeout_ms=30000,
                session_timeout_ms=10000,
            )
        except NoBrokersAvailable as exc:
            last_error = exc
            log.warning("Kafka ainda não disponível (%s/30).", attempt)
            time.sleep(2)
    raise RuntimeError(f"Não foi possível conectar ao Kafka: {last_error}")


def main() -> None:
    consumer = create_consumer()
    producer = KafkaProducer(
        bootstrap_servers=settings.kafka_servers,
        value_serializer=lambda value: json.dumps(
            value,
            ensure_ascii=False,
        ).encode("utf-8"),
        acks="all",
        retries=5,
    )
    cache = CacheService()

    log.info("Brokers: %s", ", ".join(settings.kafka_servers))
    log.info("Grupo: %s", settings.kafka_group_id)
    log.info("Consumindo: %s", ", ".join(settings.cdc_topics))

    for message in consumer:
        table = table_from_topic(message.topic)
        try:
            event = parse_debezium_message(message.value)
            result = cache.apply_event(table, event)

            if result.medicamento_id is not None:
                stock = (
                    result.stock
                    if result.stock is not None
                    else cache.current_stock(result.medicamento_id)
                )
                if (
                    stock <= settings.minimum_stock
                    and not cache.replenishment_blocked(result.medicamento_id)
                    and cache.acquire_replenishment_lock(result.medicamento_id)
                ):
                    payload = {
                        "medicamento_id": result.medicamento_id,
                        "quantidade": settings.replenishment_quantity,
                    }
                    future = producer.send(
                        settings.replenishment_topic,
                        payload,
                    )
                    future.get(timeout=15)
                    cache.save_alert(
                        result.medicamento_id,
                        settings.replenishment_quantity,
                        stock,
                    )
                    log.warning(
                        "Reabastecimento solicitado: medicamento=%s estoque=%s quantidade=%s",
                        result.medicamento_id,
                        stock,
                        settings.replenishment_quantity,
                    )

            consumer.commit()
            log.info(
                "Evento processado: tópico=%s partição=%s offset=%s operação=%s id=%s",
                message.topic,
                message.partition,
                message.offset,
                result.operation,
                result.record_id,
            )
        except (ValueError, TypeError, json.JSONDecodeError, KafkaError):
            log.exception(
                "Falha ao processar tópico=%s partição=%s offset=%s. O offset não foi confirmado.",
                message.topic,
                message.partition,
                message.offset,
            )
            time.sleep(2)
        except Exception:
            log.exception(
                "Falha inesperada em tópico=%s partição=%s offset=%s.",
                message.topic,
                message.partition,
                message.offset,
            )
            time.sleep(2)


if __name__ == "__main__":
    main()
