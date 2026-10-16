"""Modelos de entrada do emissor de NF-e/NFC-e."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# UTC-3 (America/Sao_Paulo) sem horario de verao desde 2019.
FUSO_BRASILIA = timezone(timedelta(hours=-3))


class Endereco(BaseModel):
    """Endereco no leiaute NF-e (campos obrigatorios do TEndereco)."""

    logradouro: str = Field(min_length=2, max_length=60)
    numero: str = Field(max_length=60)
    complemento: str | None = Field(default=None, max_length=60)
    bairro: str = Field(min_length=2, max_length=60)
    codigo_municipio: str = Field(description="Codigo IBGE do municipio, 7 digitos")
    municipio: str = Field(min_length=2, max_length=60)
    uf: str = Field(min_length=2, max_length=2)
    cep: str
    telefone: str | None = None

    @field_validator("codigo_municipio")
    @classmethod
    def _valida_ibge(cls, v: str) -> str:
        v = "".join(filter(str.isdigit, v))
        if len(v) != 7:
            raise ValueError("codigo_municipio deve ser o codigo IBGE de 7 digitos")
        return v

    @field_validator("uf")
    @classmethod
    def _valida_uf(cls, v: str) -> str:
        return v.upper()


class Emitente(BaseModel):
    """Dados do emitente (fixos da empresa)."""

    cnpj: str
    razao_social: str = Field(min_length=2, max_length=60)
    nome_fantasia: str | None = Field(default=None, max_length=60)
    inscricao_estadual: str
    inscricao_municipal: str | None = None
    cnae: str | None = None
    crt: Literal["1", "2", "3", "4"] = Field(
        default="1", description="1=Simples Nacional, 2=Simples c/ excesso, 3=Normal, 4=MEI"
    )
    endereco: Endereco

    @field_validator("cnpj")
    @classmethod
    def _valida_cnpj(cls, v: str) -> str:
        v = "".join(filter(str.isdigit, v))
        if len(v) != 14:
            raise ValueError("CNPJ do emitente deve ter 14 digitos")
        return v


class Destinatario(BaseModel):
    """Destinatario. A NF-e modelo 55 exige o grupo; a NFC-e pode omiti-lo."""

    cnpj: str | None = None
    cpf: str | None = None
    id_estrangeiro: str | None = None
    razao_social: str | None = Field(default=None, max_length=60)
    indicador_ie: Literal["1", "2", "9"] = "9"
    inscricao_estadual: str | None = None
    endereco: Endereco | None = None

    @field_validator("cnpj", "cpf")
    @classmethod
    def _limpa(cls, v: str | None) -> str | None:
        return "".join(filter(str.isdigit, v)) if v else None

    def identificacao(self) -> str:
        if self.cnpj:
            return f"CNPJ {self.cnpj}"
        if self.cpf:
            return f"CPF {self.cpf}"
        if self.id_estrangeiro:
            return f"idEstrangeiro {self.id_estrangeiro}"
        return "nao identificado"


class Item(BaseModel):
    """Item da nota. `csosn` para Simples Nacional, `cst_icms` para Regime Normal."""

    codigo: str = Field(max_length=60)
    descricao: str = Field(min_length=1, max_length=120)
    ncm: str
    cfop: str
    unidade: str = "UN"
    quantidade: Decimal
    valor_unitario: Decimal
    codigo_barras: str = "SEM GTIN"
    cest: str | None = None
    origem: str = "0"
    csosn: str | None = "102"
    cst_icms: str | None = None
    cst_pis: str = "49"
    cst_cofins: str = "49"
    # Grupo de ICMS-ST retido (CSOSN 500): informar os tres juntos ou nenhum.
    valor_bc_st_retido: Decimal | None = None
    percentual_st_retido: Decimal | None = None
    valor_icms_st_retido: Decimal | None = None
    info_adicional: str | None = None

    @field_validator("ncm", "cfop")
    @classmethod
    def _digitos(cls, v: str) -> str:
        return "".join(filter(str.isdigit, v))

    @model_validator(mode="after")
    def _valida_grupo_st(self) -> Item:
        informados = [
            self.valor_bc_st_retido,
            self.percentual_st_retido,
            self.valor_icms_st_retido,
        ]
        if any(v is not None for v in informados) and any(v is None for v in informados):
            raise ValueError(
                f"Item {self.codigo}: o grupo de ICMS-ST retido exige base, percentual (pST) "
                "e valor do ICMS-ST juntos — o schema da SEFAZ nao aceita o grupo incompleto"
            )
        return self

    @property
    def valor_total(self) -> Decimal:
        return (self.quantidade * self.valor_unitario).quantize(Decimal("0.01"))


class Pagamento(BaseModel):
    """Forma de pagamento. tPag 01=dinheiro, 03=cartao credito, 04=debito, 17=PIX."""

    forma: str = "01"
    valor: Decimal


class ResponsavelTecnico(BaseModel):
    """Responsavel tecnico pelo sistema emissor (grupo infRespTec).

    Exigido pela SEFAZ quando a emissao e feita por aplicativo do proprio
    contribuinte (procEmi=0). Sem os dados completos, rejeicao 972.
    id_csrt/hash_csrt so sao exigidos nas UFs que adotam o CSRT.
    """

    cnpj: str
    contato: str = Field(min_length=2, max_length=60)
    email: str = Field(min_length=6, max_length=60)
    fone: str
    id_csrt: str | None = None
    hash_csrt: str | None = None

    @field_validator("cnpj")
    @classmethod
    def _cnpj(cls, v: str) -> str:
        v = "".join(filter(str.isdigit, v))
        if len(v) != 14:
            raise ValueError("CNPJ do responsavel tecnico deve ter 14 digitos")
        return v


class DadosNota(BaseModel):
    """Payload completo de uma emissao."""

    modelo: Literal["55", "65"]
    serie: str = "1"
    numero: str
    natureza_operacao: str = "Venda de mercadoria"
    ambiente: Literal["1", "2"] = Field(default="2", description="1=producao, 2=homologacao")

    codigo_uf: str
    codigo_municipio_fato_gerador: str

    emitente: Emitente
    destinatario: Destinatario | None = None
    itens: list[Item] = Field(min_length=1)
    pagamentos: list[Pagamento] = Field(min_length=1)
    responsavel_tecnico: ResponsavelTecnico | None = None

    finalidade: str = "1"
    tipo_documento: str = "1"
    destino_operacao: str = "1"
    consumidor_final: bool = True
    indicador_presenca: str = "1"
    tipo_impressao: str | None = None
    tipo_emissao: str = "1"
    modalidade_frete: str = "9"
    processamento: str = "0"
    versao_aplicativo: str = "nfe-brasil-1.1.0"

    observacoes: str | None = Field(default=None, max_length=5000)
    data_emissao: datetime | None = None
    codigo_numerico: str | None = None

    # NFC-e: dados do QR Code (grupo infNFeSupl). Na versao 3 o QR Code online
    # e apenas <url>?p=<chave>|<versao>|<tpAmb> — nao exige mais o CSC.
    url_qrcode: str | None = None
    url_consulta_chave: str | None = None
    versao_qrcode: str = "3"

    @field_validator("codigo_municipio_fato_gerador")
    @classmethod
    def _valida_ibge(cls, v: str) -> str:
        v = "".join(filter(str.isdigit, v))
        if len(v) != 7:
            raise ValueError("codigo_municipio_fato_gerador deve ser o codigo IBGE de 7 digitos")
        return v

    def emissao(self) -> datetime:
        return self.data_emissao or datetime.now(FUSO_BRASILIA)

    def cnf(self) -> str:
        """Codigo numerico de 8 digitos (cNF)."""
        if self.codigo_numerico:
            return f"{int(self.codigo_numerico):08d}"
        return f"{secrets.randbelow(100_000_000):08d}"

    def impressao(self) -> str:
        """tpImp: 1 = DANFE retrato (NF-e), 4 = DANFE NFC-e."""
        if self.tipo_impressao:
            return self.tipo_impressao
        return "4" if self.modelo == "65" else "1"

    @property
    def valor_total(self) -> Decimal:
        return sum((i.valor_total for i in self.itens), Decimal("0.00"))
