from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class PacienteEntrada(BaseModel):
    id: int
    nome: str
    email: str
    ativo: bool = True


class MedicoEntrada(BaseModel):
    id: int
    nome: str
    especialidade: str
    ativo: bool = True


class AgendamentoEntrada(BaseModel):
    paciente: PacienteEntrada
    medico: MedicoEntrada
    horario: datetime


class ConfirmacaoResposta(BaseModel):
    codigo: str
    mensagem: str


class AgendamentoResposta(BaseModel):
    id: int
    status: str
    horario: datetime
    paciente: PacienteEntrada
    medico: MedicoEntrada
    confirmacao: ConfirmacaoResposta
    status_notificacao: str = Field(default="")


class HorariosDisponiveisResposta(BaseModel):
    id_medico: int
    data: date
    horarios: list[datetime]
