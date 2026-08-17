-- Atualização idempotente para:
-- 1) relacionar lotes e fornecedores;
-- 2) preencher registros antigos;
-- 3) tornar obrigatórias as relações essenciais do domínio.

ALTER TABLE lotes
    ADD COLUMN IF NOT EXISTS fornecedor_id INTEGER;

-- Garante um usuário operacional mesmo sem interface de login.
INSERT INTO usuarios (username, password_hash, role)
VALUES ('sistema', 'nao-utilizado-sem-login', 'sistema')
ON CONFLICT (username) DO NOTHING;

-- Garante um fornecedor para lotes antigos quando o banco ainda não possui um.
INSERT INTO fornecedores (nome, contato)
SELECT 'Fornecedor não informado', NULL
WHERE NOT EXISTS (SELECT 1 FROM fornecedores);

UPDATE lotes
SET fornecedor_id = (SELECT MIN(id) FROM fornecedores)
WHERE fornecedor_id IS NULL;

UPDATE movimentacoes
SET usuario_id = (
    SELECT id FROM usuarios WHERE username = 'sistema' LIMIT 1
)
WHERE usuario_id IS NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM lotes
        WHERE medicamento_id IS NULL OR almoxarifado_id IS NULL
    ) THEN
        RAISE EXCEPTION
            'Existem lotes sem medicamento ou almoxarifado. Corrija esses dados antes de continuar.';
    END IF;

    IF EXISTS (SELECT 1 FROM movimentacoes WHERE lote_id IS NULL) THEN
        RAISE EXCEPTION
            'Existem movimentações sem lote. Corrija esses dados antes de continuar.';
    END IF;
END
$$;

ALTER TABLE lotes
    ALTER COLUMN medicamento_id SET NOT NULL,
    ALTER COLUMN almoxarifado_id SET NOT NULL,
    ALTER COLUMN fornecedor_id SET NOT NULL;

ALTER TABLE movimentacoes
    ALTER COLUMN lote_id SET NOT NULL,
    ALTER COLUMN usuario_id SET NOT NULL,
    ALTER COLUMN data_movimentacao SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_lotes_fornecedor'
    ) THEN
        ALTER TABLE lotes
            ADD CONSTRAINT fk_lotes_fornecedor
            FOREIGN KEY (fornecedor_id)
            REFERENCES fornecedores(id)
            ON DELETE RESTRICT;
    END IF;

    ALTER TABLE movimentacoes
        DROP CONSTRAINT IF EXISTS fk_movimentacoes_usuario;

    ALTER TABLE movimentacoes
        DROP CONSTRAINT IF EXISTS movimentacoes_usuario_id_fkey;

    ALTER TABLE movimentacoes
        ADD CONSTRAINT fk_movimentacoes_usuario
        FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE RESTRICT;
END
$$;
