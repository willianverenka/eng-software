from __future__ import annotations

from typing import Any, Optional

import httpx


class ClienteNotificacaoHTTP:
    def __init__(
        self,
        base_url: str,
        token_interno: str,
        timeout: float = 5.0,
        transport: Any = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token_interno = token_interno
        self.cliente = httpx.Client(base_url=self.base_url, timeout=timeout, transport=transport)

    def enviar_email(self, email: str, assunto: str, corpo: str) -> dict[str, Any]:
        resposta = self.cliente.post(
            "/notificacoes/email",
            json={"email": email, "assunto": assunto, "corpo": corpo},
            headers={
                "Authorization": f"Bearer {self.token_interno}",
                "X-Forwarded-For": "127.0.0.1",
                "X-Real-IP": "127.0.0.1",
            },
        )
        resposta.raise_for_status()
        return resposta.json()

    def fechar(self) -> None:
        self.cliente.close()

    def __enter__(self) -> "ClienteNotificacaoHTTP":
        return self

    def __exit__(self, *_args: Any) -> None:
        self.fechar()
