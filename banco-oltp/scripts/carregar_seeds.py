#!/usr/bin/env python3
from __future__ import annotations

from datetime import date, timedelta
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.database import SessionLocal
from app.models import Almoxarifado, Fornecedor, Lote, Medicamento, Usuario

ModelT = TypeVar("ModelT")


FORNECEDORES = [
    {"nome": "Farmais", "contato": "contato@farmais.com"},
    {"nome": "MedPlus", "contato": "vendas@medplus.com"},
    {"nome": "PharmaGen", "contato": "contato@pharmagen.com"},
]

ALMOXARIFADOS = [
    {"nome": "Central", "localizacao": "Galpão A, Setor 1"},
    {"nome": "Filial Norte", "localizacao": "Galpão B, Setor 2"},
    {"nome": "Filial Sul", "localizacao": "Galpão C, Setor 3"},
]

MEDICAMENTOS = [
    {
        "nome": "Paracetamol 500mg",
        "principio_ativo": "Paracetamol",
        "laboratorio": "Eurofarma",
        "estoque_maximo": 500,
    },
    {
        "nome": "Dipirona 1g",
        "principio_ativo": "Dipirona Sódica",
        "laboratorio": "Bayer",
        "estoque_maximo": 500,
    },
    {
        "nome": "Amoxicilina 500mg",
        "principio_ativo": "Amoxicilina",
        "laboratorio": "GSK",
        "estoque_maximo": 500,
    },
    {
        "nome": "Losartana 50mg",
        "principio_ativo": "Losartana Potássica",
        "laboratorio": "Medley",
        "estoque_maximo": 500,
    },
    {
        "nome": "Atorvastatina 20mg",
        "principio_ativo": "Atorvastatina Cálcica",
        "laboratorio": "AstraZeneca",
        "estoque_maximo": 500,
    },
]


class SeedStats:
    def __init__(self) -> None:
        self.inseridos = 0
        self.existentes = 0

    def criado(self) -> None:
        self.inseridos += 1

    def existente(self) -> None:
        self.existentes += 1


def _obter_por_campo(
    session: Session,
    model: type[ModelT],
    campo: str,
    valor: object,
) -> ModelT | None:
    coluna = getattr(model, campo)
    return session.scalar(select(model).where(coluna == valor))


def _obter_ou_criar(
    session: Session,
    model: type[ModelT],
    campo_unico: str,
    dados: dict[str, object],
    stats: SeedStats,
) -> ModelT:
    existente = _obter_por_campo(
        session,
        model,
        campo_unico,
        dados[campo_unico],
    )
    if existente is not None:
        stats.existente()
        return existente

    entidade = model(**dados)
    session.add(entidade)
    session.flush()
    stats.criado()
    return entidade


def _carregar_fornecedores(
    session: Session,
    stats: SeedStats,
) -> list[Fornecedor]:
    return [
        _obter_ou_criar(
            session,
            Fornecedor,
            "nome",
            dados,
            stats,
        )
        for dados in FORNECEDORES
    ]


def _carregar_almoxarifados(
    session: Session,
    stats: SeedStats,
) -> list[Almoxarifado]:
    return [
        _obter_ou_criar(
            session,
            Almoxarifado,
            "nome",
            dados,
            stats,
        )
        for dados in ALMOXARIFADOS
    ]


def _carregar_medicamentos_e_lotes(
    session: Session,
    almoxarifados: list[Almoxarifado],
    fornecedores: list[Fornecedor],
    stats: SeedStats,
) -> None:
    validade_padrao = date.today() + timedelta(days=730)

    for dados in MEDICAMENTOS:
        medicamento = _obter_ou_criar(
            session,
            Medicamento,
            "nome",
            dados,
            stats,
        )

        for indice in range(2):
            numero_lote = f"LOTE{medicamento.id:02d}{indice:02d}"
            lote_existente = _obter_por_campo(
                session,
                Lote,
                "numero_lote",
                numero_lote,
            )

            if lote_existente is not None:
                # Nunca sobrescreve a quantidade nem a validade de um lote já
                # utilizado. Assim, reiniciar o projeto preserva o estoque e
                # todo o histórico operacional.
                stats.existente()
                continue

            session.add(
                Lote(
                    medicamento_id=medicamento.id,
                    numero_lote=numero_lote,
                    data_validade=validade_padrao,
                    quantidade=medicamento.estoque_maximo // 2,
                    almoxarifado_id=almoxarifados[
                        indice % len(almoxarifados)
                    ].id,
                    fornecedor_id=fornecedores[
                        indice % len(fornecedores)
                    ].id,
                )
            )
            session.flush()
            stats.criado()


def _carregar_usuario_admin(session: Session, stats: SeedStats) -> None:
    _obter_ou_criar(
        session,
        Usuario,
        "username",
        {
            "username": "admin",
            "password_hash": "pbkdf2:sha256:260000$...",
            "role": "admin",
        },
        stats,
    )


def main() -> None:
    stats = SeedStats()

    with SessionLocal() as session:
        try:
            fornecedores = _carregar_fornecedores(session, stats)
            almoxarifados = _carregar_almoxarifados(session, stats)
            _carregar_medicamentos_e_lotes(
                session,
                almoxarifados,
                fornecedores,
                stats,
            )
            _carregar_usuario_admin(session, stats)

            session.commit()
            print(
                "Seeds processados sem apagar dados: "
                f"{stats.inseridos} registro(s) inserido(s) e "
                f"{stats.existentes} já existente(s)."
            )
        except Exception:
            session.rollback()
            raise


if __name__ == "__main__":
    main()
