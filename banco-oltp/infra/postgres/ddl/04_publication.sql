-- AVISO: publicação Debezium idempotente da versão final local.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication WHERE pubname = 'debezium_pub'
    ) THEN
        EXECUTE 'CREATE PUBLICATION debezium_pub FOR TABLE medicamentos, lotes, movimentacoes, fornecedores, almoxarifados, usuarios';
    END IF;
END
$$;

ALTER PUBLICATION debezium_pub
SET TABLE medicamentos, lotes, movimentacoes, fornecedores, almoxarifados, usuarios;
