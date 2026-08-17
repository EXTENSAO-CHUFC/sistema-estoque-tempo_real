from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Fornecedor


class FornecedorRepository:
    def __init__(self, session: Session):
        self.session = session

    def buscar_por_id(self, fornecedor_id: int) -> Fornecedor | None:
        return self.session.get(Fornecedor, fornecedor_id)

    def buscar_primeiro(self) -> Fornecedor | None:
        return self.session.scalar(
            select(Fornecedor).order_by(Fornecedor.id.asc()).limit(1)
        )
