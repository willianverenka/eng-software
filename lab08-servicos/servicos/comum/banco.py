from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def preparar_pasta_banco(caminho: str) -> None:
    pasta = Path(caminho).expanduser().resolve().parent
    pasta.mkdir(parents=True, exist_ok=True)


def abrir_conexao_sqlite(caminho: str) -> sqlite3.Connection:
    preparar_pasta_banco(caminho)
    conexao = sqlite3.connect(caminho, check_same_thread=False)
    conexao.row_factory = sqlite3.Row
    return conexao


@contextmanager
def transacao(conexao: sqlite3.Connection) -> Iterator[sqlite3.Cursor]:
    cursor = conexao.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        yield cursor
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        cursor.close()
