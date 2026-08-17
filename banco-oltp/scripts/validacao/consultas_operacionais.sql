-- Consultas de validação operacional
-- 1. Estoque total por medicamento
SELECT m.nome AS medicamento, SUM(l.quantidade) AS estoque_total
FROM medicamentos m
JOIN lotes l ON m.id = l.medicamento_id
GROUP BY m.id, m.nome
ORDER BY estoque_total DESC;

-- 2. Estoque por almoxarifado
SELECT a.nome AS almoxarifado, m.nome AS medicamento, l.quantidade
FROM almoxarifados a
JOIN lotes l ON a.id = l.almoxtarifado_id
JOIN medicamentos m ON l.medicamento_id = m.id
ORDER BY a.nome, m.nome;

-- 3. Movimentações nas últimas 24 horas
SELECT m.nome AS medicamento, t.tipo, SUM(t.quantidade) AS quantidade
FROM movimentacoes t
JOIN lotes l ON t.lote_id = l.id
JOIN medicamentos m ON l.medicamento_id = m.id
WHERE t.data_movimentacao >= NOW() - INTERVAL '24 hours'
GROUP BY m.nome, t.tipo
ORDER BY m.nome, t.tipo;

-- 4. Lotes com validade nos próximos 30 dias (alerta)
SELECT m.nome AS medicamento, l.numero_lote, l.data_validade, l.quantidade
FROM lotes l
JOIN medicamentos m ON l.medicamento_id = m.id
WHERE l.data_validade BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days'
ORDER BY l.data_validade;

-- 5. Baixo estoque (menos de 10 unidades)
SELECT m.nome AS medicamento, l.numero_lote, l.quantidade, a.nome AS almoxarifado
FROM lotes l
JOIN medicamentos m ON l.medicamento_id = m.id
JOIN almoxarifados a ON l.almoxtarifado_id = a.id
WHERE l.quantidade < 10
ORDER BY l.quantidade ASC;