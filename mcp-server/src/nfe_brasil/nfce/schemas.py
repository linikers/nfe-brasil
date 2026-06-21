"""Schemas para NFC-e (Nota Fiscal ao Consumidor Eletrônica)."""

from pydantic import BaseModel, Field


class NFCeResponse(BaseModel):
    """Resposta da consulta de NFC-e."""
    
    chave_acesso: str = Field(description="Chave de acesso da NFC-e (44 dígitos)")
    numero: str | None = Field(None, description="Número da NFC-e")
    serie: str | None = Field(None, description="Série da NFC-e")
    modelo: int = Field(65, description="Modelo do documento (65 = NFC-e)")
    
    # Emitente
    emitente_cnpj: str | None = Field(None, description="CNPJ do emitente")
    emitente_nome: str | None = Field(None, description="Razão social do emitente")
    emitente_ie: str | None = Field(None, description="IE do emitente")
    emitente_endereco: str | None = Field(None, description="Endereço do emitente")
    
    # Consumidor
    consumidor_cpf_cnpj: str | None = Field(None, description="CPF/CNPJ do consumidor")
    consumidor_nome: str | None = Field(None, description="Nome do consumidor")
    
    # Itens
    itens: list[dict] | None = Field(None, description="Lista de itens")
    
    # Valores
    valor_total: float | None = Field(None, description="Valor total da nota")
    desconto: float | None = Field(None, description="Valor do desconto")
    valor_pago: float | None = Field(None, description="Valor pago")
    
    # Forma de pagamento
    forma_pagamento: str | None = Field(None, description="1=Dinheiro, 2=Cheque, 3=Cartão Crédito, 4=Cartão Débito, 5=Crédito Loja, 10=Vale Alimentação, 11=Vale Refeição, 12=Vale Presente, 13=Vale Combustível, 15=Boleto Bancário, 16=Depósito Bancário, 17=Pagamento Instantâneo (PIX), 18=Transferência bancário, 19=Programa fidelidade, 90=Sem pagamento, 99=Outros")
    
    # Protocolo
    numero_protocolo: str | None = Field(None, description="Número do protocolo de autorização")
    data_hora_protocolo: str | None = Field(None, description="Data/hora do protocolo")
    
    # Situação
    codigo_status: str | None = Field(None, description="Código de status da SEFAZ")
    motivo_status: str | None = Field(None, description="Motivo do status")
    
    # QR Code
    qr_code_url: str | None = Field(None, description="URL do QR Code da NFC-e")


class StatusNFCeResponse(BaseModel):
    """Resposta do status do serviço NFC-e."""
    
    sucesso: bool = Field(description="Se a consulta foi bem sucedida")
    uf: str = Field(description="UF consultada")
    status: str = Field(description="Status do serviço")
    descricao: str | None = Field(None, description="Descrição do status")
    ambiente: str = Field(description="Ambiente (produção/homologação)")
    data_hora: str | None = Field(None, description="Data/hora da consulta")
