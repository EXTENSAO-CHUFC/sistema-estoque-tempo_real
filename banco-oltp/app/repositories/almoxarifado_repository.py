from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Almoxarifado


class AlmoxarifadoRepository:
    def __init__(self, session: Session):
        self.session = session

    def buscar_por_id(self, almoxarifado_id: int) -> Almoxarifado | None:
        return self.session.get(Almoxarifado, almoxarifado_id)

    def sortear(self) -> Almoxarifado | None:
        return self.session.scalar(
            select(Almoxarifado).order_by(func.random()).limit(1)
        )
