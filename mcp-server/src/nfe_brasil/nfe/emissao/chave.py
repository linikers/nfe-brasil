"""Chave de acesso da NF-e/NFC-e: montagem (44 digitos) e validacao.

Layout da chave::

    cUF(2) AAMM(4) CNPJ(14) mod(2) serie(3) nNF(9) tpEmis(1) cNF(8) cDV(1)
"""

from __future__ import annotations

from datetime import datetime


class ChaveInvalidaError(ValueError):
    """Estrutura ou digito verificador da chave de acesso invalidos."""


def calcular_dv(base43: str) -> str:
    """Calcula o digito verificador (modulo 11, pesos 2..9 da direita para a esquerda).

    Resto da divisao:
      - 0 ou 1  -> DV 0
      - 2 a 10  -> DV = 11 - resto
    """
    if len(base43) != 43 or not base43.isdigit():
        raise ChaveInvalidaError("A base da chave deve ter 43 digitos numericos")

    soma = 0
    peso = 2
    for digito in reversed(base43):
        soma += int(digito) * peso
        peso = 2 if peso == 9 else peso + 1

    resto = soma % 11
    if resto in (0, 1):
        return "0"
    return str(11 - resto)


def montar_chave(
    *,
    codigo_uf: str,
    data_emissao: datetime,
    cnpj: str,
    modelo: str,
    serie: str,
    numero: str,
    tipo_emissao: str = "1",
    codigo_numerico: str,
) -> str:
    """Monta a chave de acesso de 44 digitos da NF-e/NFC-e."""
    cnpj = "".join(filter(str.isdigit, cnpj))
    if len(cnpj) != 14:
        raise ChaveInvalidaError(f"CNPJ do emitente deve ter 14 digitos, recebido {len(cnpj)}")

    base = (
        f"{int(codigo_uf):02d}"
        f"{data_emissao.year % 100:02d}{data_emissao.month:02d}"
        f"{cnpj}"
        f"{int(modelo):02d}"
        f"{int(serie):03d}"
        f"{int(numero):09d}"
        f"{int(tipo_emissao):01d}"
        f"{int(codigo_numerico):08d}"
    )
    if len(base) != 43:
        raise ChaveInvalidaError(f"Base da chave com {len(base)} digitos (esperado 43)")

    return base + calcular_dv(base)


def validar_chave(chave: str) -> dict[str, str]:
    """Valida estrutura e digito verificador e devolve os campos da chave."""
    chave = "".join(filter(str.isdigit, chave or ""))
    if len(chave) != 44:
        raise ChaveInvalidaError(f"Chave deve ter 44 digitos, recebido {len(chave)}")

    esperado = calcular_dv(chave[:43])
    if chave[43] != esperado:
        raise ChaveInvalidaError(f"Digito verificador invalido: informado {chave[43]}, calculado {esperado}")

    return {
        "chave": chave,
        "codigo_uf": chave[0:2],
        "ano_mes": f"{chave[4:6]}/{chave[2:4]}",
        "cnpj_emitente": chave[6:20],
        "modelo": chave[20:22],
        "serie": chave[22:25],
        "numero": chave[25:34],
        "tipo_emissao": chave[34:35],
        "codigo_numerico": chave[35:43],
        "dv": chave[43:44],
    }
