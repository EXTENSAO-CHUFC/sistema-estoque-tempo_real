#!/bin/bash
# Executado automaticamente pela imagem oficial do Postgres na primeira
# inicialização (docker-entrypoint-initdb.d roda todo .sh/.sql aqui dentro
# depois que o initdb já criou o cluster e o pg_hba.conf padrão).
#
# Não dá pra simplesmente montar infra/postgres/config/pg_hba.conf por cima do arquivo
# gerado, porque o initdb precisa rodar primeiro pra criar o cluster do
# zero — então acrescentamos as regras aqui, depois que ele já existe.
set -e

cat >> "$PGDATA/pg_hba.conf" <<'EOF'

# --- Regras adicionadas por estoque-banco (Debezium / CDC) ---
host    replication     debezium_replicator     0.0.0.0/0       md5
host    all             all                     0.0.0.0/0       md5
EOF

echo "[init-pg-hba] Regras de replicação para o Debezium adicionadas ao pg_hba.conf"