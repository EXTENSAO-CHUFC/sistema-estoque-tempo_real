from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import EventoKafkaProcessado, Lote, Medicamento
from app.repositories.almoxarifado_repository import AlmoxarifadoRepository
from app.repositories.fornecedor_repository import FornecedorRepository
from app.repositories.lote_repository import LoteRepository
from app.repositories.movimentacao_repository import MovimentacaoRepository
from app.schemas.estoque import ReabastecimentoRequest


@dataclass(frozen=True)
class ResultadoReabastecimento:
    lote: Lote
    duplicado: bool


class ReabastecimentoService:
    def __init__(self, session: Session):
        self.session = session
        self.lotes = LoteRepository(session)
        self.almoxarifados = AlmoxarifadoRepository(session)
        self.fornecedores = FornecedorRepository(session)
        self.movimentacoes = MovimentacaoRepository(session)

    def _selecionar_almoxarifado(self, almoxarifado_id: int | None):
        if almoxarifado_id is not None:
            almoxarifado = self.almoxarifados.buscar_por_id(almoxarifado_id)
            if almoxarifado is None:
                raise ValueError(
                    f"Almoxarifado {almoxarifado_id} não foi encontrado."
                )
            return almoxarifado

        almoxarifado = self.almoxarifados.sortear()
        if almoxarifado is None:
            raise RuntimeError("Nenhum almoxarifado cadastrado.")
        return almoxarifado

    def _selecionar_fornecedor(self, fornecedor_id: int | None):
        if fornecedor_id is not None:
            fornecedor = self.fornecedores.buscar_por_id(fornecedor_id)
            if fornecedor is None:
                raise ValueError(
                    f"Fornecedor {fornecedor_id} não foi encontrado."
                )
            return fornecedor

        fornecedor = self.fornecedores.buscar_primeiro()
        if fornecedor is None:
            raise RuntimeError("Nenhum fornecedor cadastrado.")
        return fornecedor

    @staticmethod
    def _gerar_numero_lote(medicamento_id: int) -> str:
        sufixo = uuid4().hex[:12].upper()
        return f"REB-{medicamento_id:04d}-{sufixo}"

    def processar(
        self,
        dados: ReabastecimentoRequest,
        evento_id: str,
        topico: str,
        particao: int,
        offset: int,
        usuario_id: int = 1,
    ) -> ResultadoReabastecimento:
        """Cria um novo lote e aplica a entrada exatamente uma vez.

        Uma nova entrega não é adicionada a um lote antigo. Cada mensagem gera
        um lote próprio, com fornecedor, almoxarifado e validade definidos.
        O registro de idempotência é salvo na mesma transação da entrada.
        """
        if not evento_id or not evento_id.strip():
            raise ValueError("evento_id é obrigatório para o reabastecimento.")

        try:
            evento_existente = self.session.get(
                EventoKafkaProcessado,
                evento_id,
            )
            if evento_existente is not None:
                lote_existente = self.session.get(
                    Lote,
                    evento_existente.lote_id,
                )
                if lote_existente is None:
                    raise RuntimeError(
                        "Evento processado referencia um lote inexistente."
                    )
                return ResultadoReabastecimento(
                    lote=lote_existente,
                    duplicado=True,
                )

            medicamento = self.session.get(Medicamento, dados.medicamento_id)
            if medicamento is None:
                raise ValueError(
                    f"Medicamento {dados.medicamento_id} não foi encontrado."
                )

            validade = dados.data_validade or (date.today() + timedelta(days=365))
            if validade <= date.today():
                raise ValueError(
                    "A validade do novo lote deve ser posterior à data atual."
                )

            fornecedor = self._selecionar_fornecedor(dados.fornecedor_id)
            almoxarifado = self._selecionar_almoxarifado(
                dados.almoxarifado_id
            )

            lote = self.lotes.adicionar(
                Lote(
                    medicamento_id=medicamento.id,
                    numero_lote=(
                        dados.numero_lote
                        or self._gerar_numero_lote(medicamento.id)
                    ),
                    data_validade=validade,
                    quantidade=dados.quantidade,
                    almoxarifado_id=almoxarifado.id,
                    fornecedor_id=fornecedor.id,
                )
            )

            self.movimentacoes.registrar(
                lote_id=lote.id,
                tipo="ENTRADA",
                quantidade=dados.quantidade,
                usuario_id=usuario_id,
            )

            self.session.add(
                EventoKafkaProcessado(
                    evento_id=evento_id,
                    topico=topico,
                    particao=particao,
                    offset_kafka=offset,
                    medicamento_id=medicamento.id,
                    lote_id=lote.id,
                )
            )

            self.session.commit()
            self.session.refresh(lote)

            return ResultadoReabastecimento(lote=lote, duplicado=False)
        except Exception:
            self.session.rollback()
            raise
