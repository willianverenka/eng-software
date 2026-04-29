# Documentacao dos Servicos - Lab 07

## Visao geral

O projeto implementa dois servicos em Python com FastAPI:

- `AgendamentoService`: registra consultas, valida horarios e orquestra o envio da notificacao.
- `NotificacaoService`: recebe pedidos de envio de e-mail e registra auditoria.

## Arquitetura adotada

- Arquitetura orientada a servicos.
- Coordenacao por **orquestracao**.
- Comunicacao entre servicos via HTTP/JSON.
- Persistencia local com SQLite.
- Execucao containerizada com Docker Compose.

Fluxo principal:

1. O cliente envia `POST /agendamentos` para o `AgendamentoService`.
2. O `AgendamentoService` valida o horario e persiste o agendamento.
3. O `AgendamentoService` chama `POST /notificacoes/email` no `NotificacaoService`.
4. Se a notificacao funcionar, o agendamento fica `CONFIRMADO`.
5. Se a notificacao falhar, o agendamento fica `PENDENTE_NOTIFICACAO`.

## Endpoints

### AgendamentoService

- `GET /saude`
- `GET /horarios-disponiveis?id_medico=<id>&data=YYYY-MM-DD`
- `POST /agendamentos`

Exemplo de payload em `POST /agendamentos`:

```json
{
  "paciente": {
    "id": 1,
    "nome": "Joao Silva",
    "email": "joao@teste.com",
    "ativo": true
  },
  "medico": {
    "id": 1,
    "nome": "Dr. Carlos Lima",
    "especialidade": "Cardiologia",
    "ativo": true
  },
  "horario": "2026-04-30T12:00:00"
}
```

### NotificacaoService

- `GET /saude`
- `POST /notificacoes/email`
- `GET /notificacoes`

Exemplo de payload em `POST /notificacoes/email`:

```json
{
  "email": "joao@teste.com",
  "assunto": "Confirmacao de agendamento",
  "corpo": "Sua consulta foi confirmada."
}
```

## Execucao

Na pasta `lab07-servicos/`:

```bash
docker compose up --build
```

Servicos expostos:

- `AgendamentoService`: porta `8001`
- `NotificacaoService`: porta `8002`

## Testes

Rodar todos os testes:

```bash
docker compose run --rm agendamento pytest testes -v
```

Rodar apenas testes unitarios:

```bash
docker compose run --rm agendamento pytest testes/testes_unitarios.py -v
```

Rodar apenas testes de integracao:

```bash
docker compose run --rm agendamento pytest testes/testes_integracao.py -v
```

Cobertura atual:

- `15` testes unitarios
- `6` testes de integracao
- total de `21` testes
