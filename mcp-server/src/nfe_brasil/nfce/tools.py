"""Ferramentas MCP para NFC-e (Nota Fiscal ao Consumidor Eletrônica)."""

import re
from ..shared.validators import validate_chave_nfe
from .._core import get_logger

logger = get_logger(__name__)


def _validar_chave_nfce(chave: str) -> bool:
    """Valida chave de acesso de NFC-e (44 dígitos, módulo 11)."""
    digitos = re.sub(r"\D", "", chave)
    if len(digitos) != 44:
        return False
    return validate_chave_nfe(digitos)


async def validar_chave_nfce(chave_acesso: str) -> dict:
    """
    Valida o formato e o dígito verificador de uma chave de acesso de NFC-e.
    
    Não consulta APIs externas - apenas verifica o cálculo matemático (módulo 11).
    
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
    
    valida = _validar_chave_nfce(digitos)
    
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
            "modelo": digitos[20:22],  # 65 = NFC-e
            "serie": digitos[22:25],
            "numero": digitos[25:34],
        })
    
    return resultado


async def consultar_nfce(chave_acesso: str) -> dict:
    """
    Consulta dados de uma NFC-e pela chave de acesso.
    
    A NFC-e (Cupom Fiscal Eletrônico) é utilizada em operações B2C
    (varejo) e não possui DANFE tradicional - apenas QR Code.
    
    Args:
        chave_acesso: Chave de acesso de 44 dígitos.
        
    Returns:
        dict com orientações de consulta.
    """
    valida = _validar_chave_nfce(chave_acesso)
    
    if not valida:
        return {
            "error": "Chave de acesso inválida",
            "chave": chave_acesso,
        }
    
    digitos = re.sub(r"\D", "", chave_acesso)
    
    # URL do QR Code (varia por estado)
    from ..shared.constants import CODIGO_UF
    cod_uf = int(digitos[:2])
    uf = CODIGO_UF.get(cod_uf, "")
    
    # URLs de consulta por estado (homologação)
    urls_consulta = {
        "AM": "https://sistemas.am.gov.br/nfce/qrcode/",
        "BA": "https://www.sefaz.ba.gov.br/NFCe/nfce.aspx",
        "CE": "https://www.nfce.sefaz.ce.gov.br/nfce/consulta",
        "GO": "https://www.nfe.sefaz.go.gov.br/nfeweb/sites/nfce/danfce",
        "MG": "https://www.nfce.mg.gov.br/nfce/qrcode",
        "MS": "https://www.sefaz.ms.gov.br/nfce/qrcode",
        "MT": "https://www.sefaz.mt.gov.br/nfse/qrcode",
        "PE": "https://www.nfce.sefaz.pe.gov.br/nfce/consulta",
        "PR": "https://www.nfe.sefaz.pr.gov.br/nfce/qrcode",
        "RS": "https://www.sefazrs.rs.gov.br/NFCE/NFCE-COM.aspx",
        "SP": "https://www.nfe.fazenda.sp.gov.br/qrcode",
    }
    
    url_consulta = urls_consulta.get(uf, f"https://www.nfe.fazenda.gov.br/portal/consultanfce.aspx")
    
    return {
        "chave_acesso": digitos,
        "modelo": 65,
        "tipo": "NFC-e (Nota Fiscal ao Consumidor Eletrônica)",
        "diferenca_nf_e": (
            "A NFC-e é diferente da NF-e: "
            "1) Destinada a consumidor final (varejo); "
            "2) Não emite DANFE tradicional (apenas QR Code); "
            "3) Contém identificação do consumidor (CPF opcional); "
            "4) Forma de pagamento é obrigatória."
        ),
        "consulta_qr_code": url_consulta,
        "orientacao": (
            "Para consultar a NFC-e, escaneie o QR Code impresso no cupom "
            "ou acesse o portal da SEFAZ do estado com a chave de acesso."
        ),
        "consulta_manual": url_consulta,
    }
