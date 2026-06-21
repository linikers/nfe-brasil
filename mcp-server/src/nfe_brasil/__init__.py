"""NFe Brasil - MCP Server + WhatsApp Bot para Notas Fiscais Brasileiras."""

__version__ = "1.0.0"
__author__ = "Liniker"
__description__ = (
    "MCP Server e WhatsApp Bot para notas fiscais brasileiras. "
    "NF-e, NFS-e, CT-e, MDF-e, NFC-e, SPED, eSocial e mais."
)

# SDK pública
from .cep import CEPClient, Endereco, validate_cep
from .certidoes import (
    CertidaoURL,
    get_cndt_url,
    get_fgts_url,
    get_pgfn_url,
    validate_cpf_for_certificate,
)
from .cnae import CNAEActivity, CNAEClass, CNAEClient
from .cpf import CPFValidation, unformat_cpf
from .empresa import EmpresaClient, EmpresaInfo
from .ibge import Estado, IBGEClient, Municipio
from .mei import MEIClient, MEIStatus
from .sdk import FiscalBrasil
from .shared.validators import (
    format_chave_nfe,
    format_cnpj,
    format_cpf,
    validate_chave_nfe,
    validate_cnpj,
    validate_cpf,
)
from .simples import SimplesClient, SimplesStatus

__all__ = [
    "CEPClient",
    "CNAEActivity",
    "CNAEClass",
    "CNAEClient",
    "CPFValidation",
    "CertidaoURL",
    "EmpresaClient",
    "EmpresaInfo",
    "Endereco",
    "Estado",
    "FiscalBrasil",
    "IBGEClient",
    "MEIClient",
    "MEIStatus",
    "Municipio",
    "SimplesClient",
    "SimplesStatus",
    "format_chave_nfe",
    "format_cnpj",
    "format_cpf",
    "get_cndt_url",
    "get_fgts_url",
    "get_pgfn_url",
    "unformat_cpf",
    "validate_cep",
    "validate_chave_nfe",
    "validate_cnpj",
    "validate_cpf",
    "validate_cpf_for_certificate",
]
