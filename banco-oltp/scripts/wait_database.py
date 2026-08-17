#!/usr/bin/env python3
"""Espera o bootstrap do OLTP terminar antes de iniciar serviços dependentes."""
from __future__ import annotations

import os
import time

import psycopg2

HOST = os.getenv("POSTGRES_HOST", "postgres")
PORT = os.getenv("POSTGRES_PORT", "5432")
DB = os.getenv("POSTGRES_DB", "estoque_banco")
USER = os.getenv("POSTGRES_USER", "estoque_banco_user")
PASSWORD = os.getenv("POSTGRES_PASSWORD", "estoque_banco_pwd")


def ready() -> bool:
    try:
        conn = psycopg2.connect(
            host=HOST,
            port=PORT,
            database=DB,
            user=USER,
            password=PASSWORD,
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT to_regclass('public.lotes');")
                if cursor.fetchone()[0] is None:
                    return False
                cursor.execute("SELECT COUNT(*) FROM lotes;")
                return int(cursor.fetchone()[0]) > 0
        finally:
            conn.close()
    except psycopg2.Error:
        return False


def main() -> None:
    for _ in range(120):
        if ready():
            print("✅ Banco OLTP e seeds disponíveis.", flush=True)
            return
        time.sleep(2)
    raise SystemExit("Banco OLTP não ficou pronto no tempo esperado.")


if __name__ == "__main__":
    main()
