from __future__ import annotations

from servicos.comum.utilitarios import normalizar_texto


RODAPE_PADRAO = "Mensagem enviada pelo MedSystem."


def assunto_e_valido(assunto: str) -> bool:
    if not isinstance(assunto, str):
        return False
    if not assunto.strip():
        return False
    for caractere in assunto:
        if ord(caractere) < 32:
            return False
    return True


def montar_corpo_email(corpo: str) -> str:
    corpo_normalizado = corpo.rstrip()
    if not corpo_normalizado:
        corpo_normalizado = ""
    return f"{corpo_normalizado}\n\n{RODAPE_PADRAO}"


def validar_tamanho_mensagem(mensagem: str, limite_caracteres: int) -> bool:
    return len(mensagem) <= limite_caracteres
