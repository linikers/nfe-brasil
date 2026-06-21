"""Ferramentas MCP para CT-e (Conhecimento de Transporte Eletrônico)."""

import re
from ..shared.validators import validate_chave_nfe
from .._core import get_logger

logger = get_logger(__name__)


def _validar_chave_cte(chave: str) -> bool:
    """Valida chave de acesso de CT-e (44 dígitos, módulo 11)."""
    digitos = re.sub(r"\D", "", chave)
    if len(digitos) != 44:
        return False
    return validate_chave_nfe(digitos)


async def validar_chave_cte(chave_acesso: str) -> dict:
    """
    Valida o formato e o dígito verificador de uma chave de acesso de CT-e.
    
    Não consulta APIs externas - apenas verifica o cálculo matemático (módulo 11).
    Extrai informações da chave: UF, data de emissão, CNPJ emitente e número.
    
    Args:
        chave_acesso: Chave de acesso com 44 dígitos.
        
    Returns:
        dict com validade e campos extraídos.
    """
    digitos = re.sub(r"\D", "", chave_acesso)
    
    if len(digitos) != 44:
        return {
            "valida": False,
            "motivo": f"Chave deve ter 44 dígitos. Recebido: {len(digitos)}",
        }
    
    valida = _validar_chave_cte(digitos)
    
    resultado = {
        "valida": valida,
        "chave_formatada": " ".join(digitos[i:i+4] for i in range(0, 44, 4)),
    }
    
    if valida:
        from ..shared.constants import CODIGO_UF
        cod_uf = int(digitos[:2])
        resultado.update({
            "uf": CODIGO_UF.get(cod_uf, f"UF {cod_uf}"),
            "ano_mes_emissao": f"{digitos[4:6]}/{digitos[2:4]}",
            "cnpj_emitente": digitos[6:20],
            "modelo": digitos[20:22],  # 57 = CT-e
            "serie": digitos[22:25],
            "numero": digitos[25:34],
        })
    
    return resultado


async def consultar_cte(chave_acesso: str) -> dict:
    """
    Consulta dados de um CT-e pela chave de acesso.
    
    ATENÇÃO: A consulta de CT-e requer certificado digital A1 para acesso
    à SEFAZ. Esta função retorna orientação sobre como acessar o CT-e.
    
    Args:
        chave_acesso: Chave de acesso de 44 dígitos.
        
    Returns:
        dict com orientações de consulta.
    """
    valida = _validar_chave_cte(chave_acesso)
    
    if not valida:
        return {
            "error": "Chave de acesso inválida",
            "chave": chave_acesso,
        }
    
    digitos = re.sub(r"\D", "", chave_acesso)
    
    return {
        "chave_acesso": digitos,
        "modelo": 57,
        "tipo": "CT-e (Conhecimento de Transporte Eletrônico)",
        "orientacao": (
            "A consulta de CT-e requer certificado digital A1. "
            "Use a tool 'baixar_cte_distribuicao' com o certificado A1 "
            "para obter os dados completos do CT-e."
        ),
        "consulta_manual": (
            "Para consulta manual, acesse: "
            "https://www.nfe.fazenda.gov.br/portal/consultacte.aspx"
        ),
    }
