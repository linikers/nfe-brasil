"""Schemas para MDF-e (Manifesto Eletrônico de Documentos Fiscais)."""

from pydantic import BaseModel, Field


class MDFeResponse(BaseModel):
    """Resposta da consulta de MDF-e."""
    
    chave_acesso: str = Field(description="Chave de acesso do MDF-e (44 dígitos)")
    numero: str | None = Field(None, description="Número do MDF-e")
    serie: str | None = Field(None, description="Série do MDF-e")
    modelo: int = Field(58, description="Modelo do documento (58 = MDF-e)")
    
    # Emitente (Transportadora)
    emitente_cnpj: str | None = Field(None, description="CNPJ do emitente")
    emitente_nome: str | None = Field(None, description="Razão social do emitente")
    emitente_ie: str | None = Field(None, description="IE do emitente")
    emitente_uf: str | None = Field(None, description="UF do emitente")
    
    # Modalidade
    modalidade: str | None = Field(None, description="0=Rodoviário, 1=Aéreo, 2=Aquaviário, 3=Ferroviário")
    
    # UF início e fim
    uf_inicio: str | None = Field(None, description="UF de início do manifesto")
    uf_fim: str | None = Field(None, description="UF de término do manifesto")
    
    # Quantidade de documentos
    qtd_documentos: int | None = Field(None, description="Quantidade de documentos fiscais")
    qtd_cte: int | None = Field(None, description="Quantidade de CT-e")
    qtd_nfe: int | None = Field(None, description="Quantidade de NF-e")
    
    # Valores
    valor_total_carga: float | None = Field(None, description="Valor total da carga")
    peso_total: float | None = Field(None, description="Peso total em kg")
    
    # Protocolo
    numero_protocolo: str | None = Field(None, description="Número do protocolo de autorização")
    data_hora_protocolo: str | None = Field(None, description="Data/hora do protocolo")
    
    # Situação
    codigo_status: str | None = Field(None, description="Código de status da SEFAZ")
    motivo_status: str | None = Field(None, description="Motivo do status")


class StatusMDFeResponse(BaseModel):
    """Resposta do status do serviço MDF-e."""
    
    sucesso: bool = Field(description="Se a consulta foi bem sucedida")
    uf: str = Field(description="UF consultada")
    status: str = Field(description="Status do serviço")
    descricao: str | None = Field(None, description="Descrição do status")
    ambiente: str = Field(description="Ambiente (produção/homologação)")
    data_hora: str | None = Field(None, description="Data/hora da consulta")
