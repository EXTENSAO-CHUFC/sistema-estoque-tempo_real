from pathlib import Path
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.config.database import get_session
from app.schemas.estoque import SaidaRequest
from app.services.estoque_service import EstoqueInsuficienteError, EstoqueService, LoteNaoEncontradoError

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "web" / "templates"))

@router.get("/")
def index(request: Request, erro: str | None = None, sucesso: str | None = None, session: Session = Depends(get_session)):
    return templates.TemplateResponse("index.html", {"request": request, "lotes": EstoqueService(session).listar_lotes(), "erro": erro, "sucesso": sucesso})

@router.get("/api/lotes")
def api_lotes(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse("_tabela_lotes.html", {"request": request, "lotes": EstoqueService(session).listar_lotes()})

@router.post("/saida")
def registrar_saida(request: Request, lote_id: int = Form(...), quantidade: int = Form(...), usuario_id: int = Form(1), session: Session = Depends(get_session)):
    try:
        payload = SaidaRequest(lote_id=lote_id, quantidade=quantidade, usuario_id=usuario_id)
        service = EstoqueService(session)
        service.registrar_saida(payload.lote_id, payload.quantidade, payload.usuario_id)
    except ValidationError as exc:
        return RedirectResponse(url=f"/?erro=Dados inválidos: {exc}", status_code=303)
    except (LoteNaoEncontradoError, EstoqueInsuficienteError) as exc:
        return RedirectResponse(url=f"/?erro={exc}", status_code=303)
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("_tabela_lotes.html", {"request": request, "lotes": service.listar_lotes()})
    return RedirectResponse(url="/?sucesso=Saída registrada com sucesso", status_code=303)

@router.get("/health")
def health(session: Session = Depends(get_session)):
    try:
        session.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "erro", "detalhe": str(exc)}



#Esse arquivo é responsável por lidar com as rotas web da aplicação, incluindo a página inicial, a listagem de lotes, o registro de saídas e a verificação de saúde do banco de dados. Ele utiliza FastAPI para criar endpoints e Jinja2 para renderizar templates HTML.