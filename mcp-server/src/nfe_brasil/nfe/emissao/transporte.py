"""Transporte SOAP 1.2 com TLS mutual auth para os webservices da SEFAZ.

Endpoints da SEFAZ do Parana (autorizador proprio, nao usa SVRS).
Fonte: tabela oficial de webservices replicada em `nfelib.nfe.client.v4_0.servers`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

import httpx

NAMESPACE_NFE = "http://www.portalfiscal.inf.br/nfe"
_NS_AUTORIZACAO = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4"
_NS_RET_AUTORIZACAO = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeRetAutorizacao4"
_NS_STATUS = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeStatusServico4"


class Servico(str, Enum):
    AUTORIZACAO = "NFeAutorizacao4"
    RET_AUTORIZACAO = "NFeRetAutorizacao4"
    CONSULTA_PROTOCOLO = "NFeConsultaProtocolo4"
    STATUS_SERVICO = "NFeStatusServico4"
    RECEPCAO_EVENTO = "NFeRecepcaoEvento4"


# UF -> base do webservice, por ambiente (1=producao, 2=homologacao).
ENDPOINTS: dict[str, dict[str, str]] = {
    "PR": {
        "1": "https://nfe.sefa.pr.gov.br/nfe",
        "2": "https://homologacao.nfe.sefa.pr.gov.br/nfe",
    },
    "SVRS": {
        "1": "https://sefazvirtual.rs.gov.br",
        "2": "https://hom1.sefazvirtual.rs.gov.br",
    },
}


class SefazError(RuntimeError):
    """Falha de comunicacao ou resposta invalida da SEFAZ."""


@dataclass(frozen=True)
class RespostaSefaz:
    """Resposta bruta de um webservice da SEFAZ."""

    servico: str
    url: str
    status_http: int
    xml: str


def endpoint(servico: Servico, ambiente: str, uf: str = "PR") -> str:
    """URL completa do webservice para a UF e ambiente informados."""
    tabela = ENDPOINTS.get(uf.upper(), ENDPOINTS["SVRS"])
    base = tabela.get(ambiente)
    if not base:
        raise SefazError(f"Ambiente desconhecido: {ambiente}")
    return f"{base}/{servico.value}"


def _envelope(ns_servico: str, conteudo: str) -> str:
    return (
        '<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
        "<soap12:Body>"
        f'<nfeDadosMsg xmlns="{ns_servico}">{conteudo}</nfeDadosMsg>'
        "</soap12:Body>"
        "</soap12:Envelope>"
    )


def _corpo_resposta(texto: str) -> str:
    """Extrai o conteudo de dentro do soap:Body da resposta."""
    sem_quebras = texto.replace("\n", "")
    casamento = re.search(
        r"<(?:soap|soapenv|env):Body[^>]*>(.*?)</(?:soap|soapenv|env):Body>",
        sem_quebras,
        re.DOTALL,
    )
    if not casamento:
        raise SefazError("Resposta da SEFAZ sem corpo SOAP reconhecivel")

    interno = casamento.group(1)
    filhos = re.findall(r"<(?![?/])([A-Za-z0-9:_.-]+)(?=[\s>/])[^>]*>(.*)</\1>", interno, re.DOTALL)
    if not filhos:
        raise SefazError("Corpo SOAP sem elemento de dados")
    return f"<{filhos[0][0]}>{filhos[0][1]}</{filhos[0][0]}>"


def enviar(
    servico: Servico,
    conteudo_xml: str,
    *,
    certificado: tuple[str, str],
    ambiente: str,
    uf: str = "PR",
    timeout: float = 40.0,
) -> RespostaSefaz:
    """Envia um XML para o webservice da SEFAZ e devolve o XML de resposta."""
    url = endpoint(servico, ambiente, uf)
    ns = {
        Servico.AUTORIZACAO: _NS_AUTORIZACAO,
        Servico.RET_AUTORIZACAO: _NS_RET_AUTORIZACAO,
        Servico.STATUS_SERVICO: _NS_STATUS,
    }.get(servico, f"http://www.portalfiscal.inf.br/nfe/wsdl/{servico.value}")

    envelope = _envelope(ns, conteudo_xml)
    cert_path, key_path = certificado

    try:
        with httpx.Client(cert=(cert_path, key_path), timeout=timeout, verify=True) as cliente:
            resposta = cliente.post(
                url,
                content=envelope.encode("utf-8"),
                headers={
                    "Content-Type": "application/soap+xml; charset=utf-8",
                    "SOAPAction": f'"{ns}/{servico.value[0].lower()}{servico.value[1:]}"',
                },
            )
    except httpx.HTTPError as exc:
        raise SefazError(f"Falha ao conectar em {url}: {exc}") from exc

    if resposta.status_code >= 500:
        raise SefazError(
            f"SEFAZ em manutencao ou indisponivel (HTTP {resposta.status_code}) em {url}"
        )

    return RespostaSefaz(
        servico=servico.value,
        url=url,
        status_http=resposta.status_code,
        xml=_corpo_resposta(resposta.text),
    )
