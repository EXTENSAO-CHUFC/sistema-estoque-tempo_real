-- AVISO: índices idempotentes para permitir reinicializações seguras.
CREATE INDEX IF NOT EXISTS idx_lotes_medicamento ON lotes(medicamento_id);
CREATE INDEX IF NOT EXISTS idx_lotes_validade ON lotes(data_validade);
CREATE INDEX IF NOT EXISTS idx_movimentacoes_lote ON movimentacoes(lote_id);
CREATE INDEX IF NOT EXISTS idx_movimentacoes_data ON movimentacoes(data_movimentacao);
