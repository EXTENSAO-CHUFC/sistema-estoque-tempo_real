from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from app.models import Lote

class LoteRepository:
    def __init__(self, session: Session):
        self.session = session

    def listar_detalhados(self) -> list[Lote]:
        stmt = (
            select(Lote)
            .options(joinedload(Lote.medicamento), joinedload(Lote.almoxarifado))
            .order_by(
                Lote.quantidade.desc(),
                Lote.medicamento_id.asc(),
                Lote.data_validade.asc(),
                Lote.numero_lote.asc(),
            )
        )
        return list(self.session.scalars(stmt).all())

    def buscar_para_atualizacao(self, lote_id: int) -> Lote | None:
        return self.session.scalar(select(Lote).where(Lote.id == lote_id).with_for_update())

    def sortear_com_estoque(self) -> Lote | None:
        return self.session.scalar(select(Lote).where(Lote.quantidade > 0).order_by(func.random()).limit(1).with_for_update())

    def buscar_mais_antigo_por_medicamento(self, medicamento_id: int) -> Lote | None:
        return self.session.scalar(select(Lote).where(Lote.medicamento_id == medicamento_id).order_by(Lote.data_validade.asc()).limit(1).with_for_update())

    def adicionar(self, lote: Lote) -> Lote:
        self.session.add(lote)
        self.session.flush()
        return lote
