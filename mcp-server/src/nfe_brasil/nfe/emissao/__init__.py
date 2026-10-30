"""Emissao de NF-e (modelo 55) e NFC-e (modelo 65) — leiaute 4.00.

Monta o XML, assina com certificado A1 (ICP-Brasil) e transmite aos
webservices da SEFAZ, tratando resposta sincrona e assincrona.

Aviso: em tpAmb=1 (producao) a nota tem valor fiscal real.
Use tpAmb=2 (homologacao) para testes.
"""

from .assinador import AssinaturaError, assinar, verificar
from .builder import construir_tnfe, montar_xml, obter_chave, serializar
from .certificado import CertificadoA1, CertificadoError
from .chave import ChaveInvalidaError, calcular_dv, montar_chave, validar_chave
from .helpers import (
    destino_operacao,
    indicador_presenca,
    modalidade_frete,
    resolver_ibge,
    tipo_documento,
)
from .emissor import ResultadoEmissao, consultar_recibo, consultar_status, emitir, montar_pacote
from .schemas import (
    DadosNota,
    Destinatario,
    Emitente,
    Endereco,
    Item,
    Pagamento,
    ResponsavelTecnico,
)
from .transporte import ENDPOINTS, SefazError, Servico, endpoint

__all__ = [
    "ENDPOINTS",
    "AssinaturaError",
    "CertificadoA1",
    "CertificadoError",
    "ChaveInvalidaError",
    "DadosNota",
    "Destinatario",
    "Emitente",
    "Endereco",
    "Item",
    "Pagamento",
    "ResponsavelTecnico",
    "ResultadoEmissao",
    "SefazError",
    "Servico",
    "assinar",
    "calcular_dv",
    "construir_tnfe",
    "consultar_recibo",
    "consultar_status",
    "emitir",
    "endpoint",
    "montar_chave",
    "montar_pacote",
    "montar_xml",
    "obter_chave",
    "serializar",
    "validar_chave",
    "verificar",
]
