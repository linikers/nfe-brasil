"""Ajuda a montar o `DadosNota` sem repetir regra em cada integração.

Campos que mudam por venda e que o chamador erra com facilidade: destino da
operação (interna × interestadual), indicador de presença, modalidade de frete,
tipo de documento do destinatário e o código IBGE do município.
"""

from __future__ import annotations

import re

import httpx

__all__ = [
    "destino_operacao",
    "indicador_presenca",
    "modalidade_frete",
    "tipo_documento",
    "resolver_ibge",
]

_BRASIL_API = "https://brasilapi.com.br/api/cep/v2"


def destino_operacao(uf_destinatario: str | None, uf_emitente: str | None) -> str:
    """1 = interna, 2 = interestadual. Sem UF de destino assume interna."""
    if not uf_destinatario or not uf_emitente:
        return "1"
    return "1" if uf_destinatario.upper() == uf_emitente.upper() else "2"


def indicador_presenca(canal: str | None) -> str:
    """1 = presencial (balcão), 2 = internet (venda online)."""
    return "1" if (canal or "").lower() in {"manual", "pdv", "balcao", "balcão"} else "2"


def modalidade_frete(valor_frete: float | None) -> str:
    """9 = sem frete (Full/marketplace), 0 = por conta do emitente."""
    return "0" if (valor_frete or 0) > 0 else "9"


def tipo_documento(documento: str | None) -> tuple[str | None, str]:
    """('cpf'|'cnpj'|None, digitos) — o schema separa CPF e CNPJ."""
    digitos = re.sub(r"\D", "", documento or "")
    if len(digitos) == 11:
        return "cpf", digitos
    if len(digitos) == 14:
        return "cnpj", digitos
    return None, digitos


def resolver_ibge(cep: str | None, *, timeout: float = 4.0) -> str | None:
    """Código IBGE (7 dígitos) do CEP. None quando não resolve.

    Falhar aqui é melhor do que emitir com município errado: a nota é recusada
    com motivo claro em vez de autorizada com dado fiscal trocado.
    """
    limpo = re.sub(r"\D", "", cep or "")
    if len(limpo) != 8:
        return None
    try:
        resposta = httpx.get(f"{_BRASIL_API}/{limpo}", timeout=timeout)
        if resposta.status_code != 200:
            return None
        dados = resposta.json()
        ibge = re.sub(r"\D", "", str(dados.get("ibge") or ""))
        return ibge if len(ibge) == 7 else None
    except Exception:
        return None
