from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Paciente:
    id: int
    nome: str
    email: str
    ativo: bool = True


@dataclass
class Medico:
    id: int
    nome: str
    especialidade: str
    ativo: bool = True


@dataclass
class Agendamento:
    id: int
    paciente: Paciente
    medico: Medico
    horario: datetime
    status: str
    hash_integridade: str
    criado_em: datetime
    atualizado_em: datetime
    status_notificacao: str = ""
    codigo_confirmacao: str = ""
    mensagem_confirmacao: str = ""


@dataclass
class Notificacao:
    id: int
    email: str
    assunto: str
    corpo: str
    status: str
    criado_em: datetime


@dataclass
class ConfirmacaoAgendamento:
    codigo: str
    mensagem: str


@dataclass
class ResultadoValidacao:
    valido: bool
    mensagem: str
    campos_invalidos: List[str] = field(default_factory=list)


@dataclass
class UsuarioAutenticado:
    sub: str
    nome: str
    email: str
    papel: str
    token: str


@dataclass
class RequisicaoAgendamento:
    paciente: Paciente
    medico: Medico
    horario: datetime


@dataclass
class RequisicaoNotificacaoEmail:
    email: str
    assunto: str
    corpo: str

