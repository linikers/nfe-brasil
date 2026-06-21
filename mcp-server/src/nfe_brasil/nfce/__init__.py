"""NFC-e (Nota Fiscal ao Consumidor Eletrônica) - Modelo 65."""

from .schemas import NFCeResponse, StatusNFCeResponse
from .tools import consultar_nfce, validar_chave_nfce

__all__ = ["NFCeResponse", "StatusNFCeResponse", "consultar_nfce", "validar_chave_nfce"]
