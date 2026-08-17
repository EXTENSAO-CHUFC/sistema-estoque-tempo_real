-- Estrutura idempotente para impedir a aplicação duplicada de mensagens Kafka.
CREATE TABLE IF NOT EXISTS eventos_kafka_processados (
    evento_id VARCHAR(255) PRIMARY KEY,
    topico VARCHAR(255) NOT NULL,
    particao INTEGER NOT NULL,
    offset_kafka BIGINT NOT NULL,
    medicamento_id INTEGER NOT NULL REFERENCES medicamentos(id),
    lote_id INTEGER NOT NULL REFERENCES lotes(id),
    processado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_evento_kafka_posicao
    ON eventos_kafka_processados(topico, particao, offset_kafka);

CREATE INDEX IF NOT EXISTS idx_eventos_kafka_processados_data
    ON eventos_kafka_processados(processado_em);
