from __future__ import annotations

import sqlite3
import threading
from datetime import date, datetime, time
from pathlib import Path
from typing import Iterable

from servicos.comum.banco import abrir_conexao_sqlite
from servicos.comum.modelos import Agendamento, Medico, Paciente
from servicos.comum.utilitarios import gerar_hash_texto


SEMENTES_MEDICOS = [
    Medico(id=1, nome="Dr. Carlos Lima", especialidade="Cardiologia"),
    Medico(id=2, nome="Dra. Ana Costa", especialidade="Cardiologia"),
    Medico(id=3, nome="Dr. Paulo Rocha", especialidade="Dermatologia"),
    Medico(id=4, nome="Dra. Julia Matos", especialidade="Ortopedia"),
    Medico(id=5, nome="Dr. Bruno Souza", especialidade="Pediatria"),
]


class ConflitoHorario(Exception):
    pass


class RepositorioAgendamentoSQLite:
    def __init__(self, caminho_banco: str):
        self.caminho_banco = caminho_banco
        self.conexao = abrir_conexao_sqlite(caminho_banco)
        self.trava = threading.Lock()
        self._inicializar()

    def _inicializar(self) -> None:
        with self.trava:
            cursor = self.conexao.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS medicos (
                    id INTEGER PRIMARY KEY,
                    nome TEXT NOT NULL,
                    especialidade TEXT NOT NULL,
                    ativo INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS agendamentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_paciente INTEGER NOT NULL,
                    nome_paciente TEXT NOT NULL,
                    email_paciente TEXT NOT NULL,
                    ativo_paciente INTEGER NOT NULL,
                    id_medico INTEGER NOT NULL,
                    nome_medico TEXT NOT NULL,
                    especialidade_medico TEXT NOT NULL,
                    ativo_medico INTEGER NOT NULL,
                    horario TEXT NOT NULL,
                    status TEXT NOT NULL,
                    status_notificacao TEXT NOT NULL,
                    codigo_confirmacao TEXT NOT NULL,
                    mensagem_confirmacao TEXT NOT NULL,
                    hash_integridade TEXT NOT NULL,
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL,
                    UNIQUE(id_medico, horario)
                )
                """
            )
            self.conexao.commit()
            cursor.close()
            self._seedar_medicos()

    def _seedar_medicos(self) -> None:
        cursor = self.conexao.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM medicos")
        total = int(cursor.fetchone()["total"])
        if total == 0:
            cursor.executemany(
                "INSERT INTO medicos (id, nome, especialidade, ativo) VALUES (?, ?, ?, ?)",
                [(medico.id, medico.nome, medico.especialidade, int(medico.ativo)) for medico in SEMENTES_MEDICOS],
            )
            self.conexao.commit()
        cursor.close()

    def listar_especialidades(self) -> list[str]:
        cursor = self.conexao.cursor()
        cursor.execute("SELECT DISTINCT especialidade FROM medicos WHERE ativo = 1 ORDER BY especialidade")
        especialidades = [linha["especialidade"] for linha in cursor.fetchall()]
        cursor.close()
        return especialidades

    def listar_medicos_por_especialidade(self, especialidade: str) -> list[Medico]:
        cursor = self.conexao.cursor()
        cursor.execute(
            "SELECT id, nome, especialidade, ativo FROM medicos WHERE ativo = 1 AND especialidade = ? ORDER BY nome",
            (especialidade,),
        )
        medicos = [
            Medico(
                id=linha["id"],
                nome=linha["nome"],
                especialidade=linha["especialidade"],
                ativo=bool(linha["ativo"]),
            )
            for linha in cursor.fetchall()
        ]
        cursor.close()
        return medicos

    def obter_medico(self, id_medico: int) -> Medico | None:
        cursor = self.conexao.cursor()
        cursor.execute(
            "SELECT id, nome, especialidade, ativo FROM medicos WHERE id = ? AND ativo = 1",
            (id_medico,),
        )
        linha = cursor.fetchone()
        cursor.close()
        if linha is None:
            return None
        return Medico(
            id=linha["id"],
            nome=linha["nome"],
            especialidade=linha["especialidade"],
            ativo=bool(linha["ativo"]),
        )

    def listar_horarios_ocupados(self, id_medico: int, data_alvo: date) -> list[datetime]:
        inicio = datetime.combine(data_alvo, time(0, 0))
        fim = datetime.combine(data_alvo, time(23, 59, 59))
        cursor = self.conexao.cursor()
        cursor.execute(
            """
            SELECT horario
            FROM agendamentos
            WHERE id_medico = ? AND horario BETWEEN ? AND ?
            ORDER BY horario
            """,
            (id_medico, inicio.isoformat(timespec="minutes"), fim.isoformat(timespec="minutes")),
        )
        horarios = [datetime.fromisoformat(linha["horario"]) for linha in cursor.fetchall()]
        cursor.close()
        return horarios

    def registrar_agendamento(
        self,
        paciente: Paciente,
        medico: Medico,
        horario: datetime,
        hash_integridade: str,
        status: str = "PENDENTE_NOTIFICACAO",
    ) -> Agendamento:
        agora = datetime.now().isoformat(timespec="seconds")
        with self.trava:
            cursor = self.conexao.cursor()
            try:
                cursor.execute("BEGIN IMMEDIATE")
                cursor.execute(
                    """
                    INSERT INTO agendamentos (
                        id_paciente, nome_paciente, email_paciente, ativo_paciente,
                        id_medico, nome_medico, especialidade_medico, ativo_medico,
                        horario, status, status_notificacao, codigo_confirmacao,
                        mensagem_confirmacao, hash_integridade, criado_em, atualizado_em
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        paciente.id,
                        paciente.nome,
                        paciente.email,
                        int(paciente.ativo),
                        medico.id,
                        medico.nome,
                        medico.especialidade,
                        int(medico.ativo),
                        horario.isoformat(timespec="minutes"),
                        status,
                        "",
                        "",
                        "",
                        hash_integridade,
                        agora,
                        agora,
                    ),
                )
                id_agendamento = cursor.lastrowid
                self.conexao.commit()
            except sqlite3.IntegrityError as excecao:
                self.conexao.rollback()
                raise ConflitoHorario("Horario ja reservado") from excecao
            finally:
                cursor.close()
        return self.obter_agendamento(id_agendamento)

    def atualizar_confirmacao(
        self,
        id_agendamento: int,
        status: str,
        status_notificacao: str,
        codigo_confirmacao: str,
        mensagem_confirmacao: str,
    ) -> Agendamento:
        atualizado_em = datetime.now().isoformat(timespec="seconds")
        with self.trava:
            cursor = self.conexao.cursor()
            cursor.execute(
                """
                UPDATE agendamentos
                SET status = ?, status_notificacao = ?, codigo_confirmacao = ?, mensagem_confirmacao = ?, atualizado_em = ?
                WHERE id = ?
                """,
                (status, status_notificacao, codigo_confirmacao, mensagem_confirmacao, atualizado_em, id_agendamento),
            )
            self.conexao.commit()
            cursor.close()
        return self.obter_agendamento(id_agendamento)

    def obter_agendamento(self, id_agendamento: int) -> Agendamento:
        cursor = self.conexao.cursor()
        cursor.execute("SELECT * FROM agendamentos WHERE id = ?", (id_agendamento,))
        linha = cursor.fetchone()
        cursor.close()
        if linha is None:
            raise ValueError("Agendamento nao encontrado")
        paciente = Paciente(
            id=linha["id_paciente"],
            nome=linha["nome_paciente"],
            email=linha["email_paciente"],
            ativo=bool(linha["ativo_paciente"]),
        )
        medico = Medico(
            id=linha["id_medico"],
            nome=linha["nome_medico"],
            especialidade=linha["especialidade_medico"],
            ativo=bool(linha["ativo_medico"]),
        )
        return Agendamento(
            id=linha["id"],
            paciente=paciente,
            medico=medico,
            horario=datetime.fromisoformat(linha["horario"]),
            status=linha["status"],
            status_notificacao=linha["status_notificacao"],
            codigo_confirmacao=linha["codigo_confirmacao"],
            mensagem_confirmacao=linha["mensagem_confirmacao"],
            hash_integridade=linha["hash_integridade"],
            criado_em=datetime.fromisoformat(linha["criado_em"]),
            atualizado_em=datetime.fromisoformat(linha["atualizado_em"]),
        )

    def listar_agendamentos_por_periodo(self, inicio: datetime, fim: datetime) -> list[Agendamento]:
        cursor = self.conexao.cursor()
        cursor.execute(
            """
            SELECT id
            FROM agendamentos
            WHERE horario BETWEEN ? AND ? AND status = 'CONFIRMADO'
            ORDER BY horario
            """,
            (inicio.isoformat(timespec="minutes"), fim.isoformat(timespec="minutes")),
        )
        ids = [linha["id"] for linha in cursor.fetchall()]
        cursor.close()
        return [self.obter_agendamento(id_agendamento) for id_agendamento in ids]
