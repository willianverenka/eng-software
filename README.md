# MedSystem

## Integrantes

- Theo Zago Zimmermann - 221230352
- Willian Verenka - 221240815
- Gabriel Lovato - 221230048
- João Vitor Sitta - 221230543
- João Rogante - 222230815


# Lab 03 — Modelo Arquitetural

## Linguagem e framework
- Escolhemos a linguagem Javascript com o framework React.js para o front-end.
- Para back-end escolhemos Python como linguagem e o framework FastAPI.

## Reuso de frameworks
- React.js para estruturar o front-end por ser padrão de indústria e apresentar vasto ecossistema de bibliotecas de componentes de interface.
- FastAPI para o back-end pela facilidade de uso e familiaridade da equipe de desenvolvedores.

## Componentes
- Componente de autenticação nativo do FastAPI
- Componente de autorização nativo do FastAPI
- Componente de mensageria assíncrona com o RabbitMQ

## Reuso de objetos e funções
- Classe para validação de dados cadastrais de pacientes e funcionários
- Classe para validação de horários ocupados em uma agenda

## Reuso de aplicações
- Integração com API de sistema de autorização de convênios e operadoras da ANS

## Reuso de bibliotecas
- Pydantic para validação de schemas da API e garantir a integração backend-frontend.
- FPDF para a geração de relatórios de agenda, consultas e receitas em PDF
- React Hook Form para validação de formulários no front-end
- Smptlib para enviar e-mails de notificação para pacientes
- Shadcn para reutilizar componentes de interface

## Reuso de padrões em arquitetura
- Orientação a serviços a fim de desacoplar as regras de negócio da aplicação e aumentar a testabilidade e futura substituição de regras.
- Arquitetura de mensageria assíncrona para melhorar a usabilidade da plataforma e a performance em requisições demoradas para o servidor, como a geração de PDFs, por exemplo.

## Interfaces

**AgendamentoService**
- listarEspecialidades()
- listarMedicosPorEspecialidade(Especialidade especialidade)
- listarHorariosDisponiveis(Medico medico, Data data)
- registrarAgendamento(Paciente paciente, Medico medico, Horario horario)
- gerarConfirmacao(Agendamento agendamento)

**AgendaService**
- buscarConsultasConfirmadas(Data dataInicio, Data dataFim)
- gerarVisualizacaoAgenda(List\<Consulta\> consultas)
- gerarDocumentoAgenda(AgendaVisualizada agenda)

**CirurgiaService**
- listarCirurgiasPendentesRevisao()
- consultarDetalhesCirurgia(Cirurgia cirurgia)
- validarInformacoesCirurgia(DetalhesCirurgia detalhes)
- anexarDocumentacao(Cirurgia cirurgia, List\<Documento\> documentos)

**AutorizacaoOperadoraService**
- submeterSolicitacaoAutorizacao(Cirurgia cirurgia, List\<Documento\> documentos)
- registrarProtocolo(Cirurgia cirurgia, Protocolo protocolo)
- atualizarStatusCirurgia(Cirurgia cirurgia, Status status)

## Componentes

### Agendamento de consultas
Interface: AgendamentoService
- listarEspecialidades()
- listarMedicosPorEspecialidade(Especialidade especialidade)
- listarHorariosDisponiveis(Medico medico, Data data)
- registrarAgendamento(Paciente paciente, Medico medico, Horario horario)
- gerarConfirmacao(Agendamento agendamento)

### Visualização de agenda
Interface: AgendaService
- buscarConsultasConfirmadas(Data dataInicio, Data dataFim)
- gerarVisualizacaoAgenda(List\<Consulta\> consultas)
- gerarDocumentoAgenda(AgendaVisualizada agenda)

### Gestão de Cirurgias e Consultas
Interface: CirurgiaService
- listarCirurgiasPendentesRevisao()
- consultarDetalhesCirurgia(Cirurgia cirurgia)
- validarInformacoesCirurgia(DetalhesCirurgia detalhes)
- anexarDocumentacao(Cirurgia cirurgia, List\<Documento\> documentos)

### Autorização da Operadora
Interface: AutorizacaoOperadoraService
- enviarSolicitacaoAutorizacao(Cirurgia cirurgia, List\<Documento\> documentos)
- registrarProtocolo(Cirurgia cirurgia, Protocolo protocolo)
- atualizarStatusCirurgia(Cirurgia cirurgia, Status status)

## Condições

**registrarAgendamento(Paciente paciente, Medico medico, Horario horario)**

Pré-condição: O paciente deve estar cadastrado e ativo no sistema; o médico deve existir e estar vinculado a uma especialidade; o horário deve estar disponível (não reservado) e pertencer a uma data futura.

Pós-condição: Um objeto Agendamento é criado com status confirmado, o horário é marcado como indisponível, o paciente e o médico são notificados.

**buscarConsultasConfirmadas(Data dataInicio, Data dataFim)**

Pré-condição: dataInicio deve ser uma data válida e anterior ou igual a dataFim.

Pós-condição: Retorna uma lista de objetos Consulta com status confirmado dentro do intervalo informado, ordenada cronologicamente.

**validarInformacoesCirurgia(DetalhesCirurgia detalhes)**

Pré-condição: O objeto DetalhesCirurgia deve estar completamente preenchido (paciente, procedimento, CID, médico responsável e data prevista); a cirurgia deve estar no status Pendente Revisão.

Pós-condição: O status da cirurgia é atualizado para Revisada em caso de sucesso, ou para Pendente Correção com os campos inválidos identificados em caso de falha.

**enviarSolicitacaoAutorizacao(Cirurgia cirurgia, List\<Documento\> documentos)**

Pré-condição: A cirurgia deve estar com status validada, a lista de documentos não deve estar vazia, o paciente deve possuir plano de saúde ativo.

Pós-condição: A solicitação é enviada à operadora, o status da cirurgia é atualizado para Aguardando Autorização, um protocolo de solicitação é gerado e associado à cirurgia.

## Dependências

![Diagrama de dependências](https://github.com/user-attachments/assets/74ad6a15-a38e-40b6-a22b-4a809d051131)

## Diagrama de componentes e interfaces

![Diagrama de componentes](https://github.com/user-attachments/assets/e515a3ee-3ddd-4850-a825-9df54f2892b2)

---

# Lab 04 — Implementação de Componentes com Interfaces

## Descrição dos dois componentes implementados

### Componente Agendamento

Responsável por toda a lógica de agendamento de consultas médicas. Gerencia especialidades disponíveis, médicos, horários livres e o registro de novos agendamentos. É o componente **provedor** nesta arquitetura — ele expõe sua interface para ser consumida por outros componentes.

### Componente Agenda

Responsável pela visualização e geração de documentos de agenda. Busca as consultas confirmadas em um período e as formata para exibição ou exportação. É o componente **cliente** nesta arquitetura — ele **depende** do Componente Agendamento para obter os dados de consultas.

## Interfaces

### Interfaces Fornecidas

#### `IAgendamentoService` — fornecida pelo Componente Agendamento

| Operação | Descrição |
|---|---|
| `listar_especialidades()` | Retorna lista de especialidades médicas disponíveis |
| `listar_medicos_por_especialidade(especialidade)` | Retorna médicos da especialidade informada |
| `listar_horarios_disponiveis(medico, data)` | Retorna horários livres de um médico em uma data |
| `registrar_agendamento(paciente, medico, horario)` | Cria e confirma um agendamento |
| `gerar_confirmacao(agendamento)` | Gera mensagem de confirmação do agendamento |
| `buscar_consultas_por_periodo(data_inicio, data_fim)` | Retorna agendamentos confirmados no período |

#### `IAgendaService` — fornecida pelo Componente Agenda

| Operação | Descrição |
|---|---|
| `buscar_consultas_confirmadas(data_inicio, data_fim)` | Recupera consultas confirmadas no período, ordenadas cronologicamente |
| `gerar_visualizacao_agenda(consultas)` | Formata a lista de consultas para exibição em tela |
| `gerar_documento_agenda(data_inicio, data_fim)` | Gera o conteúdo do documento de agenda para o período |

### Interface Requerida

O **Componente Agenda** requer a interface `IAgendamentoService` para funcionar. Ela é injetada via construtor — o componente nunca instancia diretamente a implementação concreta.



## Como ocorre a comunicação entre os componentes

A comunicação ocorre **exclusivamente por meio da interface `IAgendamentoService`**. O Componente Agenda invoca o método `buscar_consultas_por_periodo()` exposto por essa interface para obter os dados que precisa — sem conhecer nenhum detalhe interno do Componente Agendamento.

## Como foi evitado o acoplamento direto

O acoplamento direto foi evitado por meio de **injeção de dependência via interface**:

1. A interface `IAgendamentoService` é definida como uma classe abstrata (`ABC`) independente de qualquer implementação.
2. O `AgendaService` declara em seu construtor que **requer um objeto do tipo `IAgendamentoService`** — nunca `AgendamentoService` diretamente.
3. Quem monta o sistema (`main.py`) cria a implementação concreta e a **injeta** no componente cliente.

```python
# main.py — injeção de dependência manual
agendamento_service = AgendamentoService()           # implementação concreta
agenda_service = AgendaService(agendamento_service)  # injeta via interface
```

```python
# componente_agenda/agenda_service.py — depende APENAS da interface
class AgendaService(IAgendaService):
    def __init__(self, agendamento_service: IAgendamentoService):  # ← interface, não classe concreta
        self._agendamento_service = agendamento_service
```

## Estrutura do projeto

```
lab04/
│
├── componente_agendamento/          # Componente provedor
│   ├── __init__.py
│   ├── agendamento_service.py       # Implementação concreta
│   ├── interfaces/
│   │   └── i_agendamento_service.py # Interface fornecida
│   └── models/
│       └── models.py                # Modelos de domínio (Paciente, Medico, Agendamento)
│
├── componente_agenda/               # Componente cliente
│   ├── __init__.py
│   ├── agenda_service.py            # Implementação concreta
│   └── interfaces/
│       └── i_agenda_service.py      # Interface fornecida
│
├── main.py                          # Ponto de entrada e demonstração
└── README.md
```

## Instruções para execução

### Pré-requisitos

- Python 3.9 ou superior
- Nenhuma dependência externa (só biblioteca padrão)

### Como executar

```bash
# 1. Clone o repositório
git clone https://github.com/willianverenka/eng-software.git
cd eng-software/lab04

# 2. Execute o ponto de entrada
python main.py
```

### Saída esperada

```
========== MedSystem — Lab 04 ==========

>>> Especialidades disponíveis:
    - Cardiologia
    - Dermatologia
    - Ortopedia
    - Pediatria

>>> Médicos de Cardiologia:
    - Dr. Carlos Lima
    - Dra. Ana Costa

[NOTIFICAÇÃO] Paciente 'João Silva' notificado.
[NOTIFICAÇÃO] Médico 'Dr. Carlos Lima' notificado.

--- Componente Agenda ---

>>> Consultas encontradas no período: 2
=======================================================
                  AGENDA DE CONSULTAS
=======================================================
  14/03/2026 08:00 | Dr. Carlos Lima        | João Silva
  14/03/2026 08:30 | Dr. Carlos Lima        | Maria Oliveira
=======================================================
```

# Documentacao dos Servicos - Lab 08

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

