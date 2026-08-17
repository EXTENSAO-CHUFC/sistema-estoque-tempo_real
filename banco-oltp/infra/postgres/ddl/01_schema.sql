-- AVISO: schema idempotente da versão final local.
CREATE TABLE IF NOT EXISTS medicamentos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    principio_ativo VARCHAR(100),
    laboratorio VARCHAR(100),
    estoque_maximo INTEGER NOT NULL DEFAULT 500
);

CREATE TABLE IF NOT EXISTS fornecedores (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    contato VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS almoxarifados (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    localizacao VARCHAR(200)
);

CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS lotes (
    id SERIAL PRIMARY KEY,
    medicamento_id INTEGER NOT NULL REFERENCES medicamentos(id),
    numero_lote VARCHAR(50) NOT NULL,
    data_validade DATE NOT NULL,
    quantidade INTEGER NOT NULL,
    almoxarifado_id INTEGER NOT NULL REFERENCES almoxarifados(id),
    fornecedor_id INTEGER NOT NULL,
    CONSTRAINT fk_lotes_fornecedor
        FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS movimentacoes (
    id SERIAL PRIMARY KEY,
    lote_id INTEGER NOT NULL REFERENCES lotes(id),
    tipo VARCHAR(10) NOT NULL,
    quantidade INTEGER NOT NULL,
    data_movimentacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    usuario_id INTEGER NOT NULL,
    CONSTRAINT fk_movimentacoes_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS eventos_kafka_processados (
    evento_id VARCHAR(255) PRIMARY KEY,
    topico VARCHAR(255) NOT NULL,
    particao INTEGER NOT NULL,
    offset_kafka BIGINT NOT NULL,
    medicamento_id INTEGER NOT NULL REFERENCES medicamentos(id),
    lote_id INTEGER NOT NULL REFERENCES lotes(id),
    processado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_evento_kafka_posicao UNIQUE (topico, particao, offset_kafka)
);
