from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime

import httpx
from fastapi import FastAPI, HTTPException, Request, status

from servicos.agendamento.cliente_notificacao import ClienteNotificacaoHTTP
from servicos.agendamento.dominio import (
    gerar_hash_integridade,
    gerar_slots_disponiveis,
    horario_e_valido,
    montar_mensagem_confirmacao,
)
from servicos.agendamento.esquemas import (
    AgendamentoEntrada,
    AgendamentoResposta,
    ConfirmacaoResposta,
    HorariosDisponiveisResposta,
    MedicoEntrada,
    PacienteEntrada,
)
from servicos.agendamento.repositorio import ConflitoHorario, RepositorioAgendamentoSQLite
from servicos.comum.modelos import Medico, Paciente
from servicos.comum.seguranca import (
    LimitadorTaxa,
    gerar_token_jwt,
    obter_chave_jwt,
    obter_usuario_autenticado,
    verificar_ip_permitido,
    verificar_papel,
)
from servicos.comum.utilitarios import serializar_objeto


def _caminho_banco() -> str:
    return os.getenv("DATABASE_URL_AGENDAMENTO", "dados/agendamento.db")


def _base_notificacao() -> str:
    return os.getenv("URL_BASE_NOTIFICACAO", "http://127.0.0.1:8002")


def _token_servico_interno() -> str:
    return gerar_token_jwt(
        {
            "sub": "servico-agendamento",
            "nome": "Servico Agendamento",
            "email": "servico.agendamento@medsystem.local",
            "papel": "SERVICO_INTERNO",
        },
        chave=obter_chave_jwt(),
        expiracao_segundos=24 * 3600,
    )


def criar_app(
    repositorio: RepositorioAgendamentoSQLite | None = None,
    cliente_notificacao: ClienteNotificacaoHTTP | None = None,
    limitador: LimitadorTaxa | None = None,
    chave_jwt: str | None = None,
) -> FastAPI:
    app = FastAPI(title="AgendamentoService")
    repositorio = repositorio or RepositorioAgendamentoSQLite(_caminho_banco())
    cliente_notificacao = cliente_notificacao or ClienteNotificacaoHTTP(_base_notificacao(), _token_servico_interno(), timeout=5.0)
    limitador = limitador or LimitadorTaxa()
    chave_jwt = chave_jwt or obter_chave_jwt()

    @app.get("/saude")
    def saude() -> dict[str, str]:
        return {"servico": "AgendamentoService", "status": "ok"}

    @app.get("/horarios-disponiveis", response_model=HorariosDisponiveisResposta)
    def listar_horarios_disponiveis(id_medico: int, data: date, request: Request) -> dict[str, object]:
        verificar_ip_permitido(request)
        usuario = obter_usuario_autenticado(request, chave_jwt)
        verificar_papel(usuario, {"PACIENTE", "MEDICO", "RECEPCIONISTA"})
        if not limitador.permitir(f"horarios:{usuario.sub}", 15, 60):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Limite de requisicoes excedido")
        try:
            medico = repositorio.obter_medico(id_medico)
            if medico is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Medico nao encontrado")
            horarios_ocupados = repositorio.listar_horarios_ocupados(id_medico, data)
        except sqlite3.OperationalError as excecao:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Banco de dados indisponivel") from excecao
        horarios = gerar_slots_disponiveis(data, horarios_ocupados)
        return {"id_medico": id_medico, "data": data, "horarios": horarios}

    @app.post("/agendamentos", status_code=status.HTTP_201_CREATED, response_model=AgendamentoResposta)
    def registrar_agendamento(entrada: AgendamentoEntrada, request: Request) -> dict[str, object]:
        verificar_ip_permitido(request)
        usuario = obter_usuario_autenticado(request, chave_jwt)
        verificar_papel(usuario, {"PACIENTE", "RECEPCIONISTA"})

        if not horario_e_valido(entrada.horario):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Horario invalido ou fora do expediente")
        if not entrada.paciente.ativo:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Paciente inativo")

        try:
            medico_cadastrado = repositorio.obter_medico(entrada.medico.id)
            if medico_cadastrado is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Medico nao encontrado")
            if medico_cadastrado.nome != entrada.medico.nome or medico_cadastrado.especialidade != entrada.medico.especialidade:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Dados do medico nao conferem")

            paciente = Paciente(
                id=entrada.paciente.id,
                nome=entrada.paciente.nome,
                email=entrada.paciente.email,
                ativo=entrada.paciente.ativo,
            )
            medico = Medico(
                id=medico_cadastrado.id,
                nome=medico_cadastrado.nome,
                especialidade=medico_cadastrado.especialidade,
                ativo=medico_cadastrado.ativo,
            )
            hash_integridade = gerar_hash_integridade(paciente, medico, entrada.horario)
            agendamento = repositorio.registrar_agendamento(paciente, medico, entrada.horario, hash_integridade)
        except ConflitoHorario as excecao:
            raise HTTPException(status.HTTP_409_CONFLICT, str(excecao)) from excecao
        except sqlite3.OperationalError as excecao:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Banco de dados indisponivel") from excecao

        confirmacao = montar_mensagem_confirmacao(agendamento)
        status_agendamento = "PENDENTE_NOTIFICACAO"
        status_notificacao = "FALHA"

        try:
            cliente_notificacao.enviar_email(
                email=agendamento.paciente.email,
                assunto="Confirmacao de agendamento",
                corpo=confirmacao.mensagem,
            )
            status_agendamento = "CONFIRMADO"
            status_notificacao = "ENVIADA"
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError, Exception):
            pass

        try:
            agendamento = repositorio.atualizar_confirmacao(
                id_agendamento=agendamento.id,
                status=status_agendamento,
                status_notificacao=status_notificacao,
                codigo_confirmacao=confirmacao.codigo,
                mensagem_confirmacao=confirmacao.mensagem,
            )
        except sqlite3.OperationalError as excecao:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Banco de dados indisponivel") from excecao

        resposta = AgendamentoResposta(
            id=agendamento.id,
            status=agendamento.status,
            horario=agendamento.horario,
            paciente=PacienteEntrada.model_validate(serializar_objeto(agendamento.paciente)),
            medico=MedicoEntrada.model_validate(serializar_objeto(agendamento.medico)),
            confirmacao=ConfirmacaoResposta(codigo=agendamento.codigo_confirmacao, mensagem=agendamento.mensagem_confirmacao),
            status_notificacao=agendamento.status_notificacao,
        )
        return resposta.model_dump(mode="json")

    app.state.repositorio = repositorio
    app.state.cliente_notificacao = cliente_notificacao
    app.state.limitador = limitador
    return app


app = criar_app()
