-- Restrições de integridade aplicáveis tanto em bancos novos quanto existentes.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_quantidade_positiva'
    ) THEN
        ALTER TABLE lotes
            ADD CONSTRAINT chk_quantidade_positiva CHECK (quantidade >= 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_movimentacao_quantidade'
    ) THEN
        ALTER TABLE movimentacoes
            ADD CONSTRAINT chk_movimentacao_quantidade CHECK (quantidade > 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_tipo_movimentacao'
    ) THEN
        ALTER TABLE movimentacoes
            ADD CONSTRAINT chk_tipo_movimentacao
            CHECK (tipo IN ('ENTRADA', 'SAIDA'));
    END IF;
END
$$;
