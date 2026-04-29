from __future__ import annotations

import json
from datetime import datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from servicos.agendamento.cliente_notificacao import ClienteNotificacaoHTTP
from servicos.agendamento.dominio import chave_horario
from servicos.agendamento.main import criar_app as criar_app_agendamento
from servicos.agendamento.repositorio import RepositorioAgendamentoSQLite
from servicos.comum.seguranca import LimitadorTaxa, gerar_token_jwt, obter_chave_jwt
from servicos.notificacao.main import criar_app as criar_app_notificacao
from servicos.notificacao.repositorio import RepositorioNotificacaoSQLite


def _configurar_ambiente(monkeypatch: pytest.MonkeyPatch, caminho_agendamento: str, caminho_notificacao: str) -> None:
    monkeypatch.setenv("CHAVE_JWT", "chave-teste")
    monkeypatch.setenv("DATABASE_URL_AGENDAMENTO", caminho_agendamento)
    monkeypatch.setenv("DATABASE_URL_NOTIFICACAO", caminho_notificacao)
    monkeypatch.setenv("IPS_PERMITIDOS", "127.0.0.1,::1,localhost,testclient")
    monkeypatch.setenv("LIMITE_CARACTERES_MENSAGEM", "4000")
    monkeypatch.setenv("LIMITE_NOTIFICACOES_POR_MINUTO", "100")


def _token_usuario(papel: str, sub: str, nome: str, email: str) -> str:
    return gerar_token_jwt(
        {"sub": sub, "nome": nome, "email": email, "papel": papel},
        chave="chave-teste",
        expiracao_segundos=3600,
    )


def _montar_apps(monkeypatch: pytest.MonkeyPatch, tmp_path):
    caminho_agendamento = str(tmp_path / "agendamento.db")
    caminho_notificacao = str(tmp_path / "notificacao.db")
    _configurar_ambiente(monkeypatch, caminho_agendamento, caminho_notificacao)

    repositorio_notificacao = RepositorioNotificacaoSQLite(caminho_notificacao)
    app_notificacao = criar_app_notificacao(repositorio=repositorio_notificacao, limitador=LimitadorTaxa(), chave_jwt="chave-teste")
    cliente_notificacao = TestClient(app_notificacao)

    def manipulador_transport(requisicao: httpx.Request) -> httpx.Response:
        cabeçalhos = dict(requisicao.headers)
        corpo = requisicao.content.decode("utf-8")
        conteudo = json.loads(corpo) if corpo else None
        resposta = cliente_notificacao.post(
            requisicao.url.path,
            json=conteudo,
            headers={chave: valor for chave, valor in cabeçalhos.items()},
        )
        return httpx.Response(status_code=resposta.status_code, json=resposta.json())

    transporte = httpx.MockTransport(manipulador_transport)
    cliente_http = ClienteNotificacaoHTTP(
        base_url="http://notificacao:8002",
        token_interno=_token_usuario("SERVICO_INTERNO", "servico-agendamento", "Servico Agendamento", "servico.agendamento@medsystem.local"),
        timeout=5.0,
        transport=transporte,
    )
    repositorio_agendamento = RepositorioAgendamentoSQLite(caminho_agendamento)
    app_agendamento = criar_app_agendamento(
        repositorio=repositorio_agendamento,
        cliente_notificacao=cliente_http,
        limitador=LimitadorTaxa(),
        chave_jwt="chave-teste",
    )

    return TestClient(app_agendamento), cliente_notificacao, repositorio_agendamento, repositorio_notificacao


def _payload_agendamento(horario: datetime) -> dict[str, object]:
    return {
        "paciente": {"id": 1, "nome": "Joao Silva", "email": "joao@teste.com", "ativo": True},
        "medico": {"id": 1, "nome": "Dr. Carlos Lima", "especialidade": "Cardiologia", "ativo": True},
        "horario": horario.isoformat(timespec="minutes"),
    }


def test_caminho_feliz_confirma_agendamento(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    cliente_agendamento, cliente_notificacao, _, _ = _montar_apps(monkeypatch, tmp_path)
    token_paciente = _token_usuario("PACIENTE", "paciente-1", "Paciente Teste", "paciente@teste.com")
    horario = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)

    resposta = cliente_agendamento.post(
        "/agendamentos",
        json=_payload_agendamento(horario),
        headers={"Authorization": f"Bearer {token_paciente}"},
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["status"] == "CONFIRMADO"
    assert corpo["confirmacao"]["codigo"].startswith("AGD-")

    token_backoffice = _token_usuario("BACKOFFICE", "backoffice-1", "Backoffice", "backoffice@teste.com")
    auditoria = cliente_notificacao.get("/notificacoes", headers={"Authorization": f"Bearer {token_backoffice}"})
    assert auditoria.status_code == 200
    assert len(auditoria.json()) == 1


def test_notificacao_indisponivel_mantem_pendente(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    caminho_agendamento = str(tmp_path / "agendamento.db")
    caminho_notificacao = str(tmp_path / "notificacao.db")
    _configurar_ambiente(monkeypatch, caminho_agendamento, caminho_notificacao)

    def falha_transport(_requisicao: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("servico indisponivel", request=_requisicao)

    transporte = httpx.MockTransport(falha_transport)
    cliente_http = ClienteNotificacaoHTTP(
        base_url="http://notificacao:8002",
        token_interno=_token_usuario("SERVICO_INTERNO", "servico-agendamento", "Servico Agendamento", "servico.agendamento@medsystem.local"),
        timeout=5.0,
        transport=transporte,
    )
    repositorio_agendamento = RepositorioAgendamentoSQLite(caminho_agendamento)
    app_agendamento = criar_app_agendamento(
        repositorio=repositorio_agendamento,
        cliente_notificacao=cliente_http,
        limitador=LimitadorTaxa(),
        chave_jwt="chave-teste",
    )
    cliente_agendamento = TestClient(app_agendamento)
    token_paciente = _token_usuario("PACIENTE", "paciente-1", "Paciente Teste", "paciente@teste.com")
    horario = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=30, second=0, microsecond=0)

    resposta = cliente_agendamento.post(
        "/agendamentos",
        json=_payload_agendamento(horario),
        headers={"Authorization": f"Bearer {token_paciente}"},
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["status"] == "PENDENTE_NOTIFICACAO"


def test_mesmo_horario_nao_pode_ser_reservado_duas_vezes(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    cliente_agendamento, _, _, _ = _montar_apps(monkeypatch, tmp_path)
    token_paciente = _token_usuario("PACIENTE", "paciente-1", "Paciente Teste", "paciente@teste.com")
    horario = (datetime.now() + timedelta(days=1)).replace(hour=11, minute=0, second=0, microsecond=0)
    payload = _payload_agendamento(horario)

    resposta_primeira = cliente_agendamento.post(
        "/agendamentos",
        json=payload,
        headers={"Authorization": f"Bearer {token_paciente}"},
    )
    resposta_segunda = cliente_agendamento.post(
        "/agendamentos",
        json=payload,
        headers={"Authorization": f"Bearer {token_paciente}"},
    )

    assert resposta_primeira.status_code == 201
    assert resposta_segunda.status_code == 409


def test_post_notificacao_email_valido_registra_envio(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _, cliente_notificacao, _, _ = _montar_apps(monkeypatch, tmp_path)
    token_interno = _token_usuario("SERVICO_INTERNO", "servico-agendamento", "Servico Agendamento", "servico.agendamento@medsystem.local")

    resposta = cliente_notificacao.post(
        "/notificacoes/email",
        json={
            "email": "joao@teste.com",
            "assunto": "Confirmacao de agendamento",
            "corpo": "Sua consulta foi confirmada.",
        },
        headers={"Authorization": f"Bearer {token_interno}"},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "ENVIADO"
    assert corpo["email"] == "joao@teste.com"


def test_assunto_invalido_retorna_400(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _, cliente_notificacao, _, _ = _montar_apps(monkeypatch, tmp_path)
    token_interno = _token_usuario("SERVICO_INTERNO", "servico-agendamento", "Servico Agendamento", "servico.agendamento@medsystem.local")

    resposta = cliente_notificacao.post(
        "/notificacoes/email",
        json={
            "email": "joao@teste.com",
            "assunto": "   ",
            "corpo": "Conteudo",
        },
        headers={"Authorization": f"Bearer {token_interno}"},
    )

    assert resposta.status_code == 400


def test_horario_no_passado_retorna_400(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    cliente_agendamento, _, _, _ = _montar_apps(monkeypatch, tmp_path)
    token_paciente = _token_usuario("PACIENTE", "paciente-1", "Paciente Teste", "paciente@teste.com")
    horario = (datetime.now() - timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)

    resposta = cliente_agendamento.post(
        "/agendamentos",
        json=_payload_agendamento(horario),
        headers={"Authorization": f"Bearer {token_paciente}"},
    )

    assert resposta.status_code == 400
