from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class NotificacaoEntrada(BaseModel):
    email: str
    assunto: str
    corpo: str


class NotificacaoResposta(BaseModel):
    id: int
    status: str
    email: str
    assunto: str
    criado_em: datetime


class SaudeResposta(BaseModel):
    servico: str
    status: str = Field(default="ok")
