#!/usr/bin/env python3
import os
import random
import time
from datetime import datetime
from app.config.database import SessionLocal
from app.services.estoque_service import EstoqueService

INTERVALO_SEGUNDOS = int(os.getenv("SIMULATION_INTERVAL_SECONDS", "15"))

def main():
    print(f"Iniciando simulação de saída (a cada {INTERVALO_SEGUNDOS} segundos)...")
    try:
        while True:
            with SessionLocal() as session:
                resultado = EstoqueService(session).registrar_saida_aleatoria(random.randint(1, 10))
            if resultado is None:
                print("Nenhum estoque disponível. Aguardando...")
            else:
                print(f"[{datetime.now()}] Saída: {resultado.quantidade_movimentada} unidades do lote {resultado.lote_id}. Estoque restante: {resultado.quantidade_restante}")
            time.sleep(INTERVALO_SEGUNDOS)
    except KeyboardInterrupt:
        print("\nParando a simulação...")

if __name__ == "__main__":
    main()
