"""Schemas para CT-e (Conhecimento de Transporte Eletrônico)."""

from pydantic import BaseModel, Field


class CTeResponse(BaseModel):
    """Resposta da consulta de CT-e."""
    
    chave_acesso: str = Field(description="Chave de acesso do CT-e (44 dígitos)")
    numero: str | None = Field(None, description="Número do CT-e")
    serie: str | None = Field(None, description="Série do CT-e")
    modelo: int = Field(57, description="Modelo do documento (57 = CT-e)")
    
    # Emitente (Transportadora)
    emitente_cnpj: str | None = Field(None, description="CNPJ do emitente")
    emitente_nome: str | None = Field(None, description="Razão social do emitente")
    emitente_ie: str | None = Field(None, description="IE do emitente")
    
    # Remetente
    remetente_cnpj: str | None = Field(None, description="CNPJ do remetente")
    remetente_nome: str | None = Field(None, description="Nome do remetente")
    
    # Destinatário
    destinatario_cnpj: str | None = Field(None, description="CNPJ do destinatário")
    destinatario_nome: str | None = Field(None, description="Nome do destinatário")
    
    # Tomador (quem paga o frete)
    tomador_cnpj: str | None = Field(None, description="CNPJ do tomador")
    tomador_nome: str | None = Field(None, description="Nome do tomador")
    
    # Valores
    valor_total: float | None = Field(None, description="Valor total do serviço")
    valor_receber: float | None = Field(None, description="Valor a receber")
    
    # Modalidade de transporte
    modalidade: str | None = Field(None, description="Modalidade: 0=Rodoviário, 1=Aéreo, 2=Aquaviário, 3=Ferroviário, 4=Dutoviário")
    
    # CFOP
    cfop: str | None = Field(None, description="CFOP do serviço")
    
    # Protocolo
    numero_protocolo: str | None = Field(None, description="Número do protocolo de autorização")
    data_hora_protocolo: str | None = Field(None, description="Data/hora do protocolo")
    
    # Situação
    codigo_status: str | None = Field(None, description="Código de status da SEFAZ")
    motivo_status: str | None = Field(None, description="Motivo do status")


class StatusCTeResponse(BaseModel):
    """Resposta do status do serviço CT-e."""
    
    sucesso: bool = Field(description="Se a consulta foi bem sucedida")
    uf: str = Field(description="UF consultada")
    status: str = Field(description="Status do serviço")
    descricao: str | None = Field(None, description="Descrição do status")
    ambiente: str = Field(description="Ambiente (produção/homologação)")
    data_hora: str | None = Field(None, description="Data/hora da consulta")
