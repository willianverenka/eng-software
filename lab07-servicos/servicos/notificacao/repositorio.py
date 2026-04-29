from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timedelta

from servicos.comum.banco import abrir_conexao_sqlite
from servicos.comum.modelos import Notificacao


class RepositorioNotificacaoSQLite:
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
                CREATE TABLE IF NOT EXISTS notificacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    assunto TEXT NOT NULL,
                    corpo TEXT NOT NULL,
                    status TEXT NOT NULL,
                    criado_em TEXT NOT NULL
                )
                """
            )
            self.conexao.commit()
            cursor.close()

    def registrar_notificacao(self, email: str, assunto: str, corpo: str, status: str) -> Notificacao:
        criado_em = datetime.now().isoformat(timespec="seconds")
        with self.trava:
            cursor = self.conexao.cursor()
            cursor.execute(
                """
                INSERT INTO notificacoes (email, assunto, corpo, status, criado_em)
                VALUES (?, ?, ?, ?, ?)
                """,
                (email, assunto, corpo, status, criado_em),
            )
            id_notificacao = cursor.lastrowid
            self.conexao.commit()
            cursor.close()
        return self.obter_notificacao(id_notificacao)

    def listar_notificacoes(self) -> list[Notificacao]:
        cursor = self.conexao.cursor()
        cursor.execute("SELECT * FROM notificacoes ORDER BY id")
        notificacoes = [self._linha_para_notificacao(linha) for linha in cursor.fetchall()]
        cursor.close()
        return notificacoes

    def contar_notificacoes_desde(self, instante: datetime) -> int:
        cursor = self.conexao.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS total FROM notificacoes WHERE criado_em >= ?",
            (instante.isoformat(timespec="seconds"),),
        )
        total = int(cursor.fetchone()["total"])
        cursor.close()
        return total

    def obter_notificacao(self, id_notificacao: int) -> Notificacao:
        cursor = self.conexao.cursor()
        cursor.execute("SELECT * FROM notificacoes WHERE id = ?", (id_notificacao,))
        linha = cursor.fetchone()
        cursor.close()
        if linha is None:
            raise ValueError("Notificacao nao encontrada")
        return self._linha_para_notificacao(linha)

    def _linha_para_notificacao(self, linha: sqlite3.Row) -> Notificacao:
        return Notificacao(
            id=linha["id"],
            email=linha["email"],
            assunto=linha["assunto"],
            corpo=linha["corpo"],
            status=linha["status"],
            criado_em=datetime.fromisoformat(linha["criado_em"]),
        )
