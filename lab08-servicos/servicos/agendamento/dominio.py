from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Iterable

from servicos.comum.modelos import Agendamento, ConfirmacaoAgendamento, Medico, Paciente
from servicos.comum.utilitarios import gerar_chave_assinatura


HORARIO_INICIO = time(8, 0)
HORARIO_FIM = time(18, 0)
INTERVALO_MINUTOS = 30


def horario_e_valido(horario: datetime, agora: datetime | None = None) -> bool:
    if not isinstance(horario, datetime):
        return False
    agora = agora or datetime.now(tz=horario.tzinfo)
    horario_do_dia = horario.time()
    dentro_expediente = HORARIO_INICIO <= horario_do_dia <= HORARIO_FIM
    esta_no_futuro = horario > agora
    return dentro_expediente and esta_no_futuro


def chave_horario(id_medico: int, horario: datetime) -> str:
    return f"{id_medico}:{horario.strftime('%Y%m%d%H%M')}"


def gerar_hash_integridade(paciente: Paciente, medico: Medico, horario: datetime) -> str:
    return gerar_chave_assinatura(
        paciente.id,
        paciente.nome,
        paciente.email,
        paciente.ativo,
        medico.id,
        medico.nome,
        medico.especialidade,
        medico.ativo,
        horario.isoformat(timespec="minutes"),
    )


def gerar_codigo_confirmacao(agendamento: Agendamento) -> str:
    base = gerar_chave_assinatura(
        agendamento.id,
        agendamento.paciente.id,
        agendamento.medico.id,
        agendamento.horario.isoformat(timespec="minutes"),
        agendamento.hash_integridade,
    )
    return f"AGD-{agendamento.id:06d}-{base[:8].upper()}"


def montar_mensagem_confirmacao(agendamento: Agendamento) -> ConfirmacaoAgendamento:
    codigo = gerar_codigo_confirmacao(agendamento)
    mensagem = (
        f"Agendamento para {agendamento.paciente.nome} com {agendamento.medico.nome} "
        f"({agendamento.medico.especialidade}) em {agendamento.horario.strftime('%d/%m/%Y %H:%M')}."
    )
    return ConfirmacaoAgendamento(codigo=codigo, mensagem=mensagem)


def gerar_slots_disponiveis(
    data_alvo: date,
    horarios_ocupados: Iterable[datetime],
    agora: datetime | None = None,
) -> list[datetime]:
    agora = agora or datetime.now()
    ocupados = {slot.replace(second=0, microsecond=0) for slot in horarios_ocupados}
    horarios: list[datetime] = []
    atual = datetime.combine(data_alvo, HORARIO_INICIO)
    fim = datetime.combine(data_alvo, HORARIO_FIM)
    while atual <= fim:
        if horario_e_valido(atual, agora=agora) and atual.replace(second=0, microsecond=0) not in ocupados:
            horarios.append(atual)
        atual += timedelta(minutes=INTERVALO_MINUTOS)
    return horarios
