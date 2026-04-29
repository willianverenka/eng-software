from __future__ import annotations

from datetime import datetime, timedelta

from servicos.agendamento.dominio import chave_horario, horario_e_valido, montar_mensagem_confirmacao
from servicos.comum.modelos import Agendamento, Medico, Paciente
from servicos.notificacao.dominio import assunto_e_valido, montar_corpo_email


def _montar_agendamento_exemplo(status: str = "CONFIRMADO") -> Agendamento:
    paciente = Paciente(id=1, nome="Joao Silva", email="joao@teste.com", ativo=True)
    medico = Medico(id=2, nome="Dra. Ana Costa", especialidade="Cardiologia", ativo=True)
    horario = datetime(2024, 1, 2, 10, 30)
    return Agendamento(
        id=7,
        paciente=paciente,
        medico=medico,
        horario=horario,
        status=status,
        hash_integridade="hash-teste",
        criado_em=datetime(2024, 1, 1, 12, 0),
        atualizado_em=datetime(2024, 1, 1, 12, 0),
    )


class TesteDominioAgendamento:
    def test_horario_valido_no_futuro_dentro_do_expediente(self) -> None:
        agora = datetime(2024, 1, 1, 7, 0)
        horario = datetime(2024, 1, 1, 9, 0)
        assert horario_e_valido(horario, agora=agora)

    def test_horario_valido_na_abertura(self) -> None:
        agora = datetime(2024, 1, 1, 7, 59)
        horario = datetime(2024, 1, 1, 8, 0)
        assert horario_e_valido(horario, agora=agora)

    def test_horario_valido_no_fecho(self) -> None:
        agora = datetime(2024, 1, 1, 17, 59)
        horario = datetime(2024, 1, 1, 18, 0)
        assert horario_e_valido(horario, agora=agora)

    def test_horario_invalido_antes_da_abertura(self) -> None:
        agora = datetime(2024, 1, 1, 6, 0)
        horario = datetime(2024, 1, 1, 7, 59)
        assert not horario_e_valido(horario, agora=agora)

    def test_horario_invalido_apos_o_fecho(self) -> None:
        agora = datetime(2024, 1, 1, 17, 0)
        horario = datetime(2024, 1, 1, 18, 30)
        assert not horario_e_valido(horario, agora=agora)

    def test_horario_invalido_no_passado(self) -> None:
        agora = datetime(2024, 1, 1, 10, 0)
        horario = datetime(2024, 1, 1, 9, 59)
        assert not horario_e_valido(horario, agora=agora)

    def test_chave_horario_e_deterministica(self) -> None:
        horario = datetime(2024, 1, 2, 10, 30)
        chave_a = chave_horario(2, horario)
        chave_b = chave_horario(2, horario)
        assert chave_a == chave_b

    def test_chave_horario_muda_com_dados_diferentes(self) -> None:
        horario_a = datetime(2024, 1, 2, 10, 30)
        horario_b = datetime(2024, 1, 2, 11, 0)
        assert chave_horario(2, horario_a) != chave_horario(3, horario_b)

    def test_mensagem_confirmacao_e_deterministica(self) -> None:
        agendamento = _montar_agendamento_exemplo()
        mensagem_a = montar_mensagem_confirmacao(agendamento)
        mensagem_b = montar_mensagem_confirmacao(agendamento)
        assert mensagem_a == mensagem_b

    def test_mensagem_confirmacao_contem_dados_principais(self) -> None:
        agendamento = _montar_agendamento_exemplo()
        confirmacao = montar_mensagem_confirmacao(agendamento)
        assert "Joao Silva" in confirmacao.mensagem
        assert "Dra. Ana Costa" in confirmacao.mensagem
        assert "02/01/2024 10:30" in confirmacao.mensagem
        assert confirmacao.codigo.startswith("AGD-")


class TesteDominioNotificacao:
    def test_assunto_valido(self) -> None:
        assert assunto_e_valido("Confirmacao de agendamento")

    def test_assunto_vazio_e_invalido(self) -> None:
        assert not assunto_e_valido("")

    def test_assunto_com_espacos_e_invalido(self) -> None:
        assert not assunto_e_valido("   ")

    def test_assunto_com_caractere_de_controle_e_invalido(self) -> None:
        assert not assunto_e_valido("Assunto invalido\n")

    def test_corpo_email_adiciona_rodape_e_preserva_texto(self) -> None:
        corpo = "Sua consulta foi confirmada."
        resultado = montar_corpo_email(corpo)
        assert corpo in resultado
        assert "Mensagem enviada pelo MedSystem." in resultado
