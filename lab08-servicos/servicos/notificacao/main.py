from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Request, status

from servicos.comum.seguranca import (
    LimitadorTaxa,
    obter_chave_jwt,
    obter_usuario_autenticado,
    verificar_ip_permitido,
    verificar_papel,
)
from servicos.comum.utilitarios import serializar_objeto
from servicos.notificacao.dominio import assunto_e_valido, montar_corpo_email, validar_tamanho_mensagem
from servicos.notificacao.esquemas import NotificacaoEntrada, NotificacaoResposta, SaudeResposta
from servicos.notificacao.repositorio import RepositorioNotificacaoSQLite


def _caminho_banco() -> str:
    return os.getenv("DATABASE_URL_NOTIFICACAO", "dados/notificacao.db")


def criar_app(
    repositorio: RepositorioNotificacaoSQLite | None = None,
    limitador: LimitadorTaxa | None = None,
    chave_jwt: str | None = None,
) -> FastAPI:
    app = FastAPI(title="NotificacaoService")
    repositorio = repositorio or RepositorioNotificacaoSQLite(_caminho_banco())
    limitador = limitador or LimitadorTaxa()
    chave_jwt = chave_jwt or obter_chave_jwt()
    limite_caracteres = int(os.getenv("LIMITE_CARACTERES_MENSAGEM", "4000"))
    limite_por_minuto = int(os.getenv("LIMITE_NOTIFICACOES_POR_MINUTO", "100"))

    @app.get("/saude")
    def saude() -> dict[str, str]:
        return {"servico": "NotificacaoService", "status": "ok"}

    @app.post("/notificacoes/email", status_code=status.HTTP_200_OK, response_model=NotificacaoResposta)
    def enviar_email(entrada: NotificacaoEntrada, request: Request) -> dict[str, object]:
        verificar_ip_permitido(request)
        usuario = obter_usuario_autenticado(request, chave_jwt)
        verificar_papel(usuario, {"SERVICO_INTERNO"})
        if not limitador.permitir(f"notificacao:{usuario.sub}", limite_por_minuto, 60):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Limite de envio excedido")
        if not assunto_e_valido(entrada.assunto):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Assunto invalido")
        if not validar_tamanho_mensagem(entrada.corpo, limite_caracteres):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mensagem excede o limite permitido")

        corpo_formatado = montar_corpo_email(entrada.corpo)
        try:
            notificacao = repositorio.registrar_notificacao(entrada.email, entrada.assunto, corpo_formatado, "ENVIADO")
        except sqlite3.OperationalError as excecao:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Banco de dados indisponivel") from excecao
        resposta = NotificacaoResposta(
            id=notificacao.id,
            status=notificacao.status,
            email=notificacao.email,
            assunto=notificacao.assunto,
            criado_em=notificacao.criado_em,
        )
        return resposta.model_dump(mode="json")

    @app.get("/notificacoes")
    def listar_notificacoes(request: Request) -> list[dict[str, object]]:
        verificar_ip_permitido(request)
        usuario = obter_usuario_autenticado(request, chave_jwt)
        verificar_papel(usuario, {"SERVICO_INTERNO", "BACKOFFICE"})
        return [serializar_objeto(item) for item in repositorio.listar_notificacoes()]

    app.state.repositorio = repositorio
    app.state.limitador = limitador
    return app


app = criar_app()
