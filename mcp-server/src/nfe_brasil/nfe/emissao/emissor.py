"""Orquestracao da emissao: montar -> assinar -> enviar -> ler retorno."""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Any

from nfelib.nfe.bindings.v4_0.ret_envi_nfe_v4_00 import RetEnviNfe
from xsdata.formats.dataclass.parsers import XmlParser

from . import builder, transporte
from .assinador import assinar
from .certificado import CertificadoA1
from .schemas import DadosNota
from .transporte import Servico

# cStat: 100 = autorizada; 103/104/105 = lote recebido/copiado para processamento; 108 = aguardando.
STATUS_AUTORIZADA = {"100"}
STATUS_EM_PROCESSAMENTO = {"103", "104", "105"}


@dataclass
class ResultadoEmissao:
    """Resultado de uma tentativa de emissao."""

    chave: str
    ambiente: str
    codigo_status: str | None = None
    motivo: str | None = None
    protocolo: str | None = None
    recibo: str | None = None
    autorizada: bool = False
    xml_nfe: str | None = None
    xml_retorno: str | None = None
    url: str | None = None
    detalhes: dict[str, Any] = field(default_factory=dict)

    def resumo(self) -> str:
        estado = "AUTORIZADA" if self.autorizada else "NAO AUTORIZADA"
        linha = f"[{estado}] chave={self.chave} cStat={self.codigo_status} {self.motivo or ''}".strip()
        if self.protocolo:
            linha += f" protocolo={self.protocolo}"
        return linha


def _envelope_lote(xml_nfe_assinado: str) -> str:
    """Monta o <enviNFe> por concatenacao, sem re-serializar a NF-e assinada.

    Reparsear a NF-e assinada quebraria o digest XMLDSig (o C14N muda).
    """
    lote = f"{secrets.randbelow(10**15):015d}"
    return (
        f'<enviNFe xmlns="{builder.NAMESPACE_NFE}" versao="4.00">'
        f"<idLote>{lote}</idLote>"
        f"<indSinc>1</indSinc>"
        f"{xml_nfe_assinado}"
        f"</enviNFe>"
    )


def montar_pacote(
    dados: DadosNota, certificado: CertificadoA1, uf: str = "PR"
) -> tuple[str, str, str]:
    """Monta e assina a NF-e. Devolve (chave, xml_nfe_assinado, xml_enviNFe).

    Nao transmite nada — usado para conferencia/validacao previa.
    """
    chave = builder.obter_chave(dados)
    nfe = builder.construir_tnfe(dados, chave, uf)
    xml_nfe = builder.serializar(nfe)
    xml_assinado = assinar(xml_nfe, certificado, chave=chave)
    return chave, xml_assinado, _envelope_lote(xml_assinado)


def emitir(
    dados: DadosNota,
    certificado: CertificadoA1,
    *,
    enviar_de_verdade: bool = True,
    uf: str = "PR",
) -> ResultadoEmissao:
    """Emite a NF-e/NFC-e. Em homologacao a nota nao tem valor fiscal."""
    chave, xml_assinado, xml_envi = montar_pacote(dados, certificado, uf)

    resultado = ResultadoEmissao(
        chave=chave,
        ambiente=dados.ambiente,
        xml_nfe=xml_assinado,
    )

    if not enviar_de_verdade:
        resultado.codigo_status = "SIMULADO"
        resultado.motivo = "Pacote montado e assinado; transmissao desabilitada"
        return resultado

    cert_path, key_path = certificado.escrever_pem()
    resposta = transporte.enviar(
        Servico.AUTORIZACAO,
        xml_envi,
        certificado=(str(cert_path), str(key_path)),
        ambiente=dados.ambiente,
        uf=uf,
        modelo=dados.modelo,
    )
    resultado.xml_retorno = resposta.xml
    resultado.url = resposta.url

    retorno: Any = XmlParser().from_string(resposta.xml, RetEnviNfe)
    resultado.codigo_status = str(retorno.cStat) if retorno.cStat is not None else None
    resultado.motivo = retorno.xMotivo

    if retorno.infRec is not None:
        resultado.recibo = retorno.infRec.nRec

    if retorno.protNFe is not None and retorno.protNFe.infProt is not None:
        protocolo = retorno.protNFe.infProt
        resultado.codigo_status = str(protocolo.cStat)
        resultado.motivo = protocolo.xMotivo
        resultado.protocolo = protocolo.nProt
        resultado.autorizada = str(protocolo.cStat) in STATUS_AUTORIZADA
        resultado.detalhes["data_autorizacao"] = str(protocolo.dhRecbto)

    if not resultado.autorizada and resultado.recibo:
        resultado.detalhes["observacao"] = (
            "Lote em processamento assincrono: consulte o recibo em NFeRetAutorizacao4"
        )

    return resultado


def consultar_recibo(
    recibo: str,
    certificado: CertificadoA1,
    *,
    ambiente: str,
    uf: str = "PR",
    modelo: str = "55",
) -> ResultadoEmissao:
    """Consulta o resultado do lote assincrono (NFeRetAutorizacao4)."""
    consulta = (
        '<consReciNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">'
        f"<tpAmb>{ambiente}</tpAmb><nRec>{recibo}</nRec></consReciNFe>"
    )
    cert_path, key_path = certificado.escrever_pem()
    resposta = transporte.enviar(
        Servico.RET_AUTORIZACAO,
        consulta,
        certificado=(str(cert_path), str(key_path)),
        ambiente=ambiente,
        uf=uf,
        modelo=modelo,
    )

    retorno: Any = XmlParser().from_string(resposta.xml)
    resultado = ResultadoEmissao(
        chave="",
        ambiente=ambiente,
        recibo=recibo,
        xml_retorno=resposta.xml,
        url=resposta.url,
    )
    resultado.codigo_status = str(getattr(retorno, "cStat", "") or "") or None
    resultado.motivo = getattr(retorno, "xMotivo", None)

    protocolos = getattr(retorno, "protNFe", None) or []
    if protocolos:
        inf = protocolos[0].infProt
        resultado.chave = inf.chNFe or ""
        resultado.codigo_status = str(inf.cStat)
        resultado.motivo = inf.xMotivo
        resultado.protocolo = inf.nProt
        resultado.autorizada = str(inf.cStat) in STATUS_AUTORIZADA

    return resultado


def consultar_status(
    certificado: CertificadoA1, *, ambiente: str, uf: str = "PR", modelo: str = "55"
) -> dict[str, str]:
    """Consulta o status do servico de autorizacao (NFeStatusServico4)."""
    consulta = (
        '<consStatServ xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">'
        f"<tpAmb>{ambiente}</tpAmb><cUF>{transporte.codigo_uf(uf)}</cUF><xServ>STATUS</xServ>"
        "</consStatServ>"
    )
    cert_path, key_path = certificado.escrever_pem()
    resposta = transporte.enviar(
        Servico.STATUS_SERVICO,
        consulta,
        certificado=(str(cert_path), str(key_path)),
        ambiente=ambiente,
        uf=uf,
        modelo=modelo,
    )
    retorno: Any = XmlParser().from_string(resposta.xml)
    return {
        "cStat": str(getattr(retorno, "cStat", "")),
        "xMotivo": str(getattr(retorno, "xMotivo", "")),
        "dhRecbto": str(getattr(retorno, "dhRecbto", "")),
        "url": resposta.url,
    }


__all__ = [
    "ResultadoEmissao",
    "consultar_recibo",
    "consultar_status",
    "emitir",
    "montar_pacote",
]
