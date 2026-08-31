#!/usr/bin/env python3
"""Consome pedidos de reabastecimento do Kafka e grava ENTRADA no PostgreSQL.

Garantias aplicadas neste consumer:
- o offset só é confirmado depois do commit da transação no PostgreSQL;
- mensagens inválidas são registradas e descartadas de forma controlada;
- falhas transitórias não avançam o offset e a mensagem é tentada novamente;
- cada mensagem Kafka possui um identificador idempotente baseado em
  tópico, partição e offset, evitando entradas duplicadas após reentrega.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from enum import Enum
from typing import Any

from kafka import KafkaConsumer
from kafka.errors import KafkaError, NoBrokersAvailable
from kafka.structs import OffsetAndMetadata, TopicPartition
from pydantic import ValidationError

from app.config.database import SessionLocal
from app.config.settings import settings
from app.schemas.estoque import ReabastecimentoRequest
from app.services.reabastecimento_service import ReabastecimentoService


class ResultadoProcessamento(str, Enum):
    SUCESSO = "SUCESSO"
    INVALIDA = "INVALIDA"
    TENTAR_NOVAMENTE = "TENTAR_NOVAMENTE"


def _identificador_evento(message: Any) -> str:
    """Cria um identificador estável para a mensagem Kafka.

    Caso o produtor já envie ``evento_id``, ele é preservado. Caso contrário,
    tópico, partição e offset formam uma identidade única e reproduzível.
    """
    payload = message.value if isinstance(message.value, dict) else {}
    evento_id = payload.get("evento_id")
    if evento_id:
        return str(evento_id)
    return f"kafka:{message.topic}:{message.partition}:{message.offset}"


def process_message(message: Any) -> ResultadoProcessamento:
    payload = message.value
    evento_id = _identificador_evento(message)

    try:
        dados = ReabastecimentoRequest.model_validate(payload)
    except ValidationError as exc:
        print(
            f"[{datetime.now()}] Mensagem inválida descartada: "
            f"evento_id={evento_id}, payload={payload}, erro={exc}"
        )
        return ResultadoProcessamento.INVALIDA

    try:
        with SessionLocal() as session:
            resultado = ReabastecimentoService(session).processar(
                dados=dados,
                evento_id=evento_id,
                topico=message.topic,
                particao=message.partition,
                offset=message.offset,
            )

        if resultado.duplicado:
            print(
                f"[{datetime.now()}] Evento já processado, sem nova entrada: "
                f"evento_id={evento_id}, lote={resultado.lote.id}."
            )
        else:
            print(
                f"[{datetime.now()}] Reabastecimento confirmado: "
                f"evento_id={evento_id}, +{dados.quantidade} unidade(s), "
                f"lote={resultado.lote.id}, medicamento={dados.medicamento_id}, "
                f"novo_estoque_lote={resultado.lote.quantidade}."
            )

        return ResultadoProcessamento.SUCESSO
    except Exception as exc:
        print(
            f"[{datetime.now()}] Falha ao processar mensagem; "
            f"o offset não será confirmado: evento_id={evento_id}, "
            f"payload={payload}, erro={exc}"
        )
        return ResultadoProcessamento.TENTAR_NOVAMENTE


def _confirmar_mensagem(consumer: KafkaConsumer, message: Any) -> None:
    """Confirma somente a mensagem processada, sem avançar outras partições."""
    topic_partition = TopicPartition(message.topic, message.partition)
    consumer.commit(
        offsets={
            topic_partition: OffsetAndMetadata(message.offset + 1,
                "",
                getattr(message, "leader_epoch", None),
            )
        }

    )


def _criar_consumer() -> KafkaConsumer:
    return KafkaConsumer(
        settings.kafka_topic_reabastecimento,
        bootstrap_servers=[
            server.strip()
            for server in settings.kafka_bootstrap_servers.split(",")
            if server.strip()
        ],
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        group_id="reabastecimento-group",
        value_deserializer=lambda raw: json.loads(raw.decode("utf-8")),
    )


def _consumir(consumer: KafkaConsumer) -> None:
    print(
        "Consumidor conectado com commit manual. "
        f"Tópico: '{settings.kafka_topic_reabastecimento}'."
    )

    for message in consumer:
        print(
            f"Mensagem recebida: tópico={message.topic}, "
            f"partição={message.partition}, offset={message.offset}, "
            f"payload={message.value}"
        )

        resultado = process_message(message)

        if resultado in {
            ResultadoProcessamento.SUCESSO,
            ResultadoProcessamento.INVALIDA,
        }:
            _confirmar_mensagem(consumer, message)
            continue

        topic_partition = TopicPartition(message.topic, message.partition)
        consumer.seek(topic_partition, message.offset)
        time.sleep(settings.kafka_reconnect_seconds)


def main() -> None:
    print(
        "Consumidor de reabastecimento iniciado. "
        "Aguardando o Kafka ficar disponível..."
    )

    while True:
        consumer: KafkaConsumer | None = None
        try:
            consumer = _criar_consumer()
            _consumir(consumer)
        except KeyboardInterrupt:
            print("\nDesligando o consumidor...")
            return
        except (NoBrokersAvailable, KafkaError, OSError) as exc:
            print(
                f"Kafka indisponível ({exc}). Nova tentativa em "
                f"{settings.kafka_reconnect_seconds}s."
            )
            time.sleep(settings.kafka_reconnect_seconds)
        except Exception as exc:
            print(
                f"Falha inesperada no consumidor ({exc}). Nova tentativa em "
                f"{settings.kafka_reconnect_seconds}s."
            )
            time.sleep(settings.kafka_reconnect_seconds)
        finally:
            if consumer is not None:
                consumer.close()


if __name__ == "__main__":
    main()
