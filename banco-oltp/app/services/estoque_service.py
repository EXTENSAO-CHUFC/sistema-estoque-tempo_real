from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.repositories.lote_repository import LoteRepository
from app.repositories.movimentacao_repository import MovimentacaoRepository


class EstoqueError(Exception):
    """Erro base das regras de negócio do estoque."""


class LoteNaoEncontradoError(EstoqueError):
    """Indica que o lote informado não existe."""


class QuantidadeInvalidaError(EstoqueError):
    """Indica que a quantidade da movimentação não é positiva."""

    def __init__(self, quantidade: int):
        self.quantidade = quantidade
        super().__init__(
            "A quantidade deve ser um número inteiro maior que zero."
        )


class EstoqueInsuficienteError(EstoqueError):
    """Indica que o lote não possui estoque suficiente para a saída."""

    def __init__(self, disponivel: int):
        self.disponivel = disponivel
        super().__init__(
            f"Estoque insuficiente (disponível: {disponivel})"
        )


@dataclass(frozen=True)
class ResultadoMovimentacao:
    lote_id: int
    quantidade_movimentada: int
    quantidade_restante: int


class EstoqueService:
    def __init__(self, session: Session):
        self.session = session
        self.lotes = LoteRepository(session)
        self.movimentacoes = MovimentacaoRepository(session)

    @staticmethod
    def _validar_quantidade(quantidade: int) -> None:
        # A validação permanece na camada de serviço para proteger todos os
        # pontos de entrada: interface web, scripts, testes e consumers.
        if isinstance(quantidade, bool) or not isinstance(quantidade, int):
            raise QuantidadeInvalidaError(quantidade)
        if quantidade <= 0:
            raise QuantidadeInvalidaError(quantidade)

    def listar_lotes(self) -> list[dict]:
        return [
            {
                "lote_id": lote.id,
                "numero_lote": lote.numero_lote,
                "quantidade": lote.quantidade,
                "data_validade": lote.data_validade,
                "medicamento": lote.medicamento.nome,
                "almoxarifado": lote.almoxarifado.nome,
            }
            for lote in self.lotes.listar_detalhados()
        ]

    def registrar_saida(
        self,
        lote_id: int,
        quantidade: int,
        usuario_id: int = 1,
    ) -> ResultadoMovimentacao:
        self._validar_quantidade(quantidade)

        try:
            lote = self.lotes.buscar_para_atualizacao(lote_id)
            if lote is None:
                raise LoteNaoEncontradoError("Lote não encontrado")

            if quantidade > lote.quantidade:
                raise EstoqueInsuficienteError(lote.quantidade)

            lote.quantidade -= quantidade
            self.movimentacoes.registrar(
                lote.id,
                "SAIDA",
                quantidade,
                usuario_id,
            )
            self.session.commit()

            return ResultadoMovimentacao(
                lote_id=lote.id,
                quantidade_movimentada=quantidade,
                quantidade_restante=lote.quantidade,
            )
        except Exception:
            self.session.rollback()
            raise

    def registrar_saida_aleatoria(
        self,
        quantidade: int,
        usuario_id: int = 1,
    ) -> ResultadoMovimentacao | None:
        self._validar_quantidade(quantidade)

        try:
            lote = self.lotes.sortear_com_estoque()
            if lote is None:
                self.session.rollback()
                return None

            retirada = min(quantidade, lote.quantidade)
            lote.quantidade -= retirada
            self.movimentacoes.registrar(
                lote.id,
                "SAIDA",
                retirada,
                usuario_id,
            )
            self.session.commit()

            return ResultadoMovimentacao(
                lote_id=lote.id,
                quantidade_movimentada=retirada,
                quantidade_restante=lote.quantidade,
            )
        except Exception:
            self.session.rollback()
            raise

#Arquivo responsável por gerenciar a lógica de negócios relacionada ao estoque de medicamentos, incluindo a listagem de lotes, o registro de saídas e a verificação de disponibilidade de estoque. Ele utiliza repositórios para interagir com o banco de dados e define exceções personalizadas para lidar com erros específicos do domínio do estoque.