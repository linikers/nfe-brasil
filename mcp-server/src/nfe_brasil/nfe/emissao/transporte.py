"""Transporte SOAP 1.2 com TLS mutual auth para os webservices da SEFAZ.

No Parana a NF-e (modelo 55) e a NFC-e (modelo 65) usam hosts diferentes:
  NF-e  -> nfe.sefa.pr.gov.br
  NFC-e -> nfce.sefa.pr.gov.br

Fontes: tabela de webservices da SEFA/PR (sped.fazenda.pr.gov.br) e
`nfelib.nfe.client.v4_0.servers`.
"""

from __future__ import annotations

import os
import ssl
from dataclasses import dataclass
from enum import Enum

import httpx

# httpx usa o bundle do certifi por padrao, que nao tem as raizes ICP-Brasil.
# Os servidores da SEFAZ usam cadeia ICP-Brasil (AC Raiz v10), entao apontamos
# para o trust store do sistema — onde a raiz oficial esta instalada.
CA_BUNDLE_PADRAO = "/etc/ssl/certs/ca-certificates.crt"


def contexto_tls(ca_bundle: str | None = None) -> ssl.SSLContext:
    """Contexto TLS mutual auth para os webservices da SEFAZ.

    O TLS e fixado em 1.2: os servidores da SEFAZ-PR nao completam o handshake
    em TLS 1.3 (respondem *handshake failure* / *bad certificate*).
    """
    caminho = ca_bundle or os.environ.get("SEFAZ_CA_BUNDLE") or CA_BUNDLE_PADRAO
    contexto = ssl.create_default_context(cafile=caminho if os.path.exists(caminho) else None)
    contexto.minimum_version = ssl.TLSVersion.TLSv1_2
    contexto.maximum_version = ssl.TLSVersion.TLSv1_2
    return contexto

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


# UF -> modelo -> ambiente -> base do webservice (1=producao, 2=homologacao).
ENDPOINTS: dict[str, dict[str, dict[str, str]]] = {
    "PR": {
        "55": {
            "1": "https://nfe.sefa.pr.gov.br/nfe",
            "2": "https://homologacao.nfe.sefa.pr.gov.br/nfe",
        },
        "65": {
            "1": "https://nfce.sefa.pr.gov.br/nfce",
            "2": "https://homologacao.nfce.sefa.pr.gov.br/nfce",
        },
    },
    "SVRS": {
        "55": {
            "1": "https://sefazvirtual.rs.gov.br",
            "2": "https://hom1.sefazvirtual.rs.gov.br",
        },
        "65": {
            "1": "https://nfce.sefazvirtual.rs.gov.br",
            "2": "https://hom1.nfce.sefazvirtual.rs.gov.br",
        },
    },
}

# URL de consulta publica do QR Code e de consulta por chave (grupo infNFeSupl).
URLS_QRCODE: dict[str, dict[str, str]] = {
    "PR": {"65": "http://www.fazenda.pr.gov.br/nfce/qrcode"},
}
URLS_CONSULTA_CHAVE: dict[str, dict[str, str]] = {
    "PR": {"65": "http://www.fazenda.pr.gov.br/nfce/consulta"},
}

# Codigo IBGE da UF (campo cUF do leiaute).
CODIGO_UF: dict[str, str] = {
    "RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17",
    "MA": "21", "PI": "22", "CE": "23", "RN": "24", "PB": "25", "PE": "26", "AL": "27",
    "SE": "28", "BA": "29", "MG": "31", "ES": "32", "RJ": "33", "SP": "35",
    "PR": "41", "SC": "42", "RS": "43", "MS": "50", "MT": "51", "GO": "52", "DF": "53",
}


def codigo_uf(uf: str) -> str:
    """Codigo IBGE (cUF) da UF."""
    codigo = CODIGO_UF.get(uf.upper())
    if not codigo:
        raise SefazError(f"UF desconhecida: {uf}")
    return codigo


class SefazError(RuntimeError):
    """Falha de comunicacao ou resposta invalida da SEFAZ."""


@dataclass(frozen=True)
class RespostaSefaz:
    """Resposta bruta de um webservice da SEFAZ."""

    servico: str
    url: str
    status_http: int
    xml: str


def endpoint(servico: Servico, ambiente: str, uf: str = "PR", modelo: str = "55") -> str:
    """URL completa do webservice para UF, modelo e ambiente informados."""
    por_uf = ENDPOINTS.get(uf.upper(), ENDPOINTS["SVRS"])
    base = por_uf.get(modelo, por_uf["55"]).get(ambiente)
    if not base:
        raise SefazError(f"Ambiente desconhecido: {ambiente}")
    return f"{base}/{servico.value}"


def url_qrcode(uf: str = "PR", modelo: str = "65") -> str | None:
    """URL de consulta publica do QR Code da NFC-e no estado."""
    return URLS_QRCODE.get(uf.upper(), {}).get(modelo)


def url_consulta_chave(uf: str = "PR", modelo: str = "65") -> str | None:
    """URL de consulta por chave de acesso (campo urlChave do infNFeSupl)."""
    return URLS_CONSULTA_CHAVE.get(uf.upper(), {}).get(modelo)


def _envelope(ns_servico: str, conteudo: str) -> str:
    return (
        '<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
        "<soap12:Body>"
        f'<nfeDadosMsg xmlns="{ns_servico}">{conteudo}</nfeDadosMsg>'
        "</soap12:Body>"
        "</soap12:Envelope>"
    )


def _corpo_resposta(texto: str) -> str:
    """Extrai o elemento de dados de dentro do soap:Body da resposta.

    A resposta vem como <soap:Body><nfeResultMsg><retEnviNFe>...</...>: o parser
    do leiaute precisa do elemento interno, nao do envelope.
    """
    try:
        from lxml import etree

        raiz = etree.fromstring(texto.encode("utf-8") if isinstance(texto, str) else texto)
    except Exception as exc:
        raise SefazError("Resposta da SEFAZ nao e XML valido") from exc

    corpo = None
    for elemento in raiz.iter():
        nome = etree.QName(elemento)
        if nome.localname == "Body" and (nome.namespace or "").startswith(
            "http://www.w3.org/2003/05/soap"
        ):
            corpo = elemento
            break

    if corpo is None or len(corpo) == 0:
        raise SefazError("Resposta da SEFAZ sem corpo SOAP reconhecivel")

    dados = corpo[0]
    while (
        len(dados) > 0
        and isinstance(dados[0].tag, str)
        and etree.QName(dados).localname.lower().startswith("nferesultmsg")
    ):
        dados = dados[0]

    return str(etree.tostring(dados, encoding="unicode"))


def enviar(
    servico: Servico,
    conteudo_xml: str,
    *,
    certificado: tuple[str, str],
    ambiente: str,
    uf: str = "PR",
    modelo: str = "55",
    timeout: float = 40.0,
) -> RespostaSefaz:
    """Envia um XML para o webservice da SEFAZ e devolve o XML de resposta."""
    url = endpoint(servico, ambiente, uf, modelo)
    ca_bundle = os.environ.get("SEFAZ_CA_BUNDLE") or CA_BUNDLE_PADRAO
    ns = {
        Servico.AUTORIZACAO: _NS_AUTORIZACAO,
        Servico.RET_AUTORIZACAO: _NS_RET_AUTORIZACAO,
        Servico.STATUS_SERVICO: _NS_STATUS,
    }.get(servico, f"http://www.portalfiscal.inf.br/nfe/wsdl/{servico.value}")

    envelope = _envelope(ns, conteudo_xml)
    cert_path, key_path = certificado

    try:
        with httpx.Client(
            cert=(cert_path, key_path), timeout=timeout, verify=contexto_tls(ca_bundle)
        ) as cliente:
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
