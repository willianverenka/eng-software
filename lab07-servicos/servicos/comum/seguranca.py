from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import threading
import time
from collections import defaultdict, deque
from typing import Any, Dict, Iterable, Optional

from fastapi import HTTPException, Request, status

from .modelos import UsuarioAutenticado


def obter_chave_jwt() -> str:
    return os.getenv("CHAVE_JWT", "chave-de-desenvolvimento")


def obter_ips_permitidos() -> set[str]:
    brutos = os.getenv("IPS_PERMITIDOS", "127.0.0.1,::1,localhost,testclient")
    return {item.strip() for item in brutos.split(",") if item.strip()}


def _codificar_base64_url(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).decode("utf-8").rstrip("=")


def _decodificar_base64_url(dados: str) -> bytes:
    preenchimento = "=" * (-len(dados) % 4)
    return base64.urlsafe_b64decode(dados + preenchimento)


def gerar_token_jwt(claims: Dict[str, Any], chave: Optional[str] = None, expiracao_segundos: int = 3600) -> str:
    chave = chave or obter_chave_jwt()
    agora = int(time.time())
    payload = dict(claims)
    payload.setdefault("iat", agora)
    payload.setdefault("exp", agora + expiracao_segundos)
    cabecalho = {"alg": "HS256", "typ": "JWT"}
    parte_cabecalho = _codificar_base64_url(json.dumps(cabecalho, separators=(",", ":")).encode("utf-8"))
    parte_payload = _codificar_base64_url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    mensagem = f"{parte_cabecalho}.{parte_payload}".encode("utf-8")
    assinatura = hmac.new(chave.encode("utf-8"), mensagem, hashlib.sha256).digest()
    return f"{parte_cabecalho}.{parte_payload}.{_codificar_base64_url(assinatura)}"


def decodificar_token_jwt(token: str, chave: Optional[str] = None) -> Dict[str, Any]:
    chave = chave or obter_chave_jwt()
    partes = token.split(".")
    if len(partes) != 3:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token JWT invalido")
    parte_cabecalho, parte_payload, parte_assinatura = partes
    mensagem = f"{parte_cabecalho}.{parte_payload}".encode("utf-8")
    assinatura_esperada = hmac.new(chave.encode("utf-8"), mensagem, hashlib.sha256).digest()
    assinatura_fornecida = _decodificar_base64_url(parte_assinatura)
    if not hmac.compare_digest(assinatura_esperada, assinatura_fornecida):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Assinatura do token invalida")
    payload = json.loads(_decodificar_base64_url(parte_payload).decode("utf-8"))
    agora = int(time.time())
    if int(payload.get("exp", 0)) < agora:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expirado")
    return payload


def extrair_token_bearer(cabecalho_autorizacao: Optional[str]) -> str:
    if not cabecalho_autorizacao:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Cabecalho Authorization ausente")
    partes = cabecalho_autorizacao.strip().split(" ", 1)
    if len(partes) != 2 or partes[0].lower() != "bearer" or not partes[1].strip():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Formato de Authorization invalido")
    return partes[1].strip()


def obter_usuario_autenticado(request: Request, chave_jwt: Optional[str] = None) -> UsuarioAutenticado:
    token = extrair_token_bearer(request.headers.get("authorization"))
    dados = decodificar_token_jwt(token, chave_jwt)
    return UsuarioAutenticado(
        sub=str(dados.get("sub", "")),
        nome=str(dados.get("nome", "")),
        email=str(dados.get("email", "")),
        papel=str(dados.get("papel", "")),
        token=token,
    )


def verificar_papel(usuario: UsuarioAutenticado, papeis_permitidos: Iterable[str]) -> None:
    permitidos = {papel.upper() for papel in papeis_permitidos}
    if usuario.papel.upper() not in permitidos:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Papel nao autorizado")


def verificar_ip_permitido(request: Request, ips_permitidos: Optional[Iterable[str]] = None) -> None:
    permitidos = {item for item in (ips_permitidos or obter_ips_permitidos())}
    candidatos: list[str] = []
    if request.client and request.client.host:
        candidatos.append(request.client.host)
    for cabecalho in ("x-forwarded-for", "x-real-ip"):
        valor = request.headers.get(cabecalho)
        if valor:
            candidatos.extend([item.strip() for item in valor.split(",") if item.strip()])
    if not any(candidato in permitidos for candidato in candidatos):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "IP nao autorizado")


class LimitadorTaxa:
    def __init__(self) -> None:
        self._registros = defaultdict(deque)
        self._trava = threading.Lock()

    def permitir(self, chave: str, limite: int, janela_segundos: int) -> bool:
        agora = time.time()
        with self._trava:
            fila = self._registros[chave]
            while fila and agora - fila[0] > janela_segundos:
                fila.popleft()
            if len(fila) >= limite:
                return False
            fila.append(agora)
            return True


def gerar_chave_assinatura(*partes: Any) -> str:
    texto = "|".join(str(parte) for parte in partes)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()
