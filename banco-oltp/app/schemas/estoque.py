from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class SaidaRequest(BaseModel):
    lote_id: int
    quantidade: int = Field(gt=0)
    usuario_id: int = 1


class ReabastecimentoRequest(BaseModel):
    medicamento_id: int
    quantidade: int = Field(gt=0)

    # Campos opcionais para uma entrada real. O produtor atual pode continuar
    # enviando somente medicamento_id e quantidade.
    numero_lote: str | None = Field(default=None, min_length=1, max_length=50)
    data_validade: date | None = None
    fornecedor_id: int | None = Field(default=None, gt=0)
    almoxarifado_id: int | None = Field(default=None, gt=0)
