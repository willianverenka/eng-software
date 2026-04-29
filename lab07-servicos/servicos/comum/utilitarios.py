from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, time
from typing import Any


def serializar_objeto(objeto: Any) -> Any:
    if is_dataclass(objeto):
        return {chave: serializar_objeto(valor) for chave, valor in asdict(objeto).items()}
    if isinstance(objeto, datetime):
        return objeto.isoformat(timespec="minutes")
    if isinstance(objeto, date):
        return objeto.isoformat()
    if isinstance(objeto, time):
        return objeto.isoformat(timespec="minutes")
    if isinstance(objeto, dict):
        return {chave: serializar_objeto(valor) for chave, valor in objeto.items()}
    if isinstance(objeto, list):
        return [serializar_objeto(valor) for valor in objeto]
    if isinstance(objeto, tuple):
        return [serializar_objeto(valor) for valor in objeto]
    return objeto


def parse_iso_datetime(valor: Any) -> datetime:
    if isinstance(valor, datetime):
        return valor
    if not isinstance(valor, str):
        raise ValueError("Valor de data e hora invalido")
    texto = valor.replace("Z", "+00:00")
    return datetime.fromisoformat(texto)


def parse_iso_date(valor: Any) -> date:
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor
    if not isinstance(valor, str):
        raise ValueError("Valor de data invalido")
    return date.fromisoformat(valor)


def gerar_hash_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def gerar_chave_assinatura(*partes: Any) -> str:
    texto = "|".join(str(parte) for parte in partes)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def normalizar_texto(texto: str) -> str:
    return " ".join(texto.split()) if texto else ""


def carregar_json_texto(texto: str) -> Any:
    if not texto:
        return None
    return json.loads(texto)
