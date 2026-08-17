from sqlalchemy.orm import Session
from app.models import Movimentacao

class MovimentacaoRepository:
    def __init__(self, session: Session):
        self.session = session

    def registrar(self, lote_id: int, tipo: str, quantidade: int, usuario_id: int = 1) -> Movimentacao:
        mov = Movimentacao(lote_id=lote_id, tipo=tipo, quantidade=quantidade, usuario_id=usuario_id)
        self.session.add(mov)
        self.session.flush()
        return mov
