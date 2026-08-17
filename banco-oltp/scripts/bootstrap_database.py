#!/usr/bin/env python3
"""Prepara o PostgreSQL OLTP para a versão final local.

AVISO: este script é idempotente e foi adicionado para permitir que o
monorepo seja iniciado somente com `docker compose up -d --build`.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import psycopg2

BASE_DIR = Path(__file__).resolve().parents[1]

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "estoque_banco")
POSTGRES_USER = os.getenv("POSTGRES_USER", "estoque_banco_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "estoque_banco_pwd")


def connection():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )


def wait_for_postgres(timeout: int = 120) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            conn = connection()
            conn.close()
            print("✅ PostgreSQL disponível.", flush=True)
            return
        except psycopg2.OperationalError as exc:
            last_error = exc
            time.sleep(2)
    raise RuntimeError(f"PostgreSQL não ficou disponível: {last_error}")


def apply_sql(relative_path: str) -> None:
    path = BASE_DIR / relative_path
    print(f"→ Aplicando {relative_path}", flush=True)
    conn = connection()
    try:
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute(path.read_text(encoding="utf-8-sig"))
    finally:
        conn.close()


def main() -> None:
    wait_for_postgres()

    for relative_path in [
        "infra/postgres/ddl/01_schema.sql",
        "infra/postgres/ddl/02_indexes.sql",
        "infra/postgres/ddl/03_constraints.sql",
        "infra/postgres/ddl/04_publication.sql",
        "infra/postgres/ddl/05_consumer_idempotencia.sql",
        "infra/postgres/ddl/06_lotes_fornecedores_not_null.sql",
        "infra/postgres/roles/01_replication_user.sql",
    ]:
        apply_sql(relative_path)

    # Import local só depois do schema existir.
    from scripts.carregar_seeds import main as load_seeds

    print("🌱 Carregando seeds sem sobrescrever dados existentes...", flush=True)
    load_seeds()
    print("✅ Banco OLTP preparado.", flush=True)


if __name__ == "__main__":
    main()
