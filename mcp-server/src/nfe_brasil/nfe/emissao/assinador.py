"""Assinatura digital XMLDSig da NF-e/NFC-e com certificado A1 (ICP-Brasil).

A NF-e 4.00 exige assinatura enveloped sobre `<infNFe Id="NFe<44 digitos>">` com:
  - CanonicalizationMethod : C14N 1.0
  - SignatureMethod        : RSA-SHA1
  - DigestMethod           : SHA-1
  - Transforms             : enveloped-signature + C14N 1.0

O signxml desabilita SHA-1 por padrao por ser inseguro em geral; o leiaute da
NF-e ainda o exige, entao o override abaixo e deliberado e restrito a este fluxo.
"""

from __future__ import annotations

from lxml import etree
from signxml.algorithms import (
    CanonicalizationMethod,
    DigestAlgorithm,
    SignatureConstructionMethod,
    SignatureMethod,
)
from signxml.signer import XMLSigner
from signxml.verifier import SignatureConfiguration, XMLVerifier

from .certificado import CertificadoA1
from .chave import validar_chave

NAMESPACE_NFE = "http://www.portalfiscal.inf.br/nfe"


class AssinaturaError(ValueError):
    """Falha ao assinar ou verificar o XML."""


class AssinadorNFe(XMLSigner):
    """XMLSigner que aceita SHA-1, exigido pelo leiaute da NF-e 4.00."""

    def check_deprecated_methods(self) -> None:
        return None


def assinar(
    xml: str | bytes,
    certificado: CertificadoA1,
    *,
    chave: str | None = None,
    id_elemento: str | None = None,
) -> str:
    """Assina o XML da NF-e e devolve a string assinada (sem quebras de linha)."""
    dados = xml.encode("utf-8") if isinstance(xml, str) else xml
    raiz = etree.fromstring(dados)

    if id_elemento is None:
        if chave:
            id_elemento = f"NFe{chave}"
        else:
            inf = raiz.find(f"{{{NAMESPACE_NFE}}}infNFe")
            if inf is None or not inf.get("Id"):
                raise AssinaturaError("XML sem infNFe/Id e sem chave informada")
            id_elemento = inf.get("Id")

    so_digitos = (id_elemento or "").removeprefix("NFe")
    if so_digitos:
        validar_chave(so_digitos)

    assinador = AssinadorNFe(
        method=SignatureConstructionMethod.enveloped,
        signature_algorithm=SignatureMethod.RSA_SHA1,
        digest_algorithm=DigestAlgorithm.SHA1,
        c14n_algorithm=CanonicalizationMethod.CANONICAL_XML_1_0,
    )

    raiz_assinada = assinador.sign(
        raiz,
        key=certificado.chave_pem,
        cert=certificado.certificado_pem.decode("utf-8"),
        reference_uri=f"#{id_elemento}",
    )

    return str(
        etree.tostring(raiz_assinada, encoding="unicode", xml_declaration=False)
        .replace("\n", "")
        .replace("\r", "")
    )


def _titular_do_xml(raiz: etree._Element) -> str | None:
    """Le o CN do certificado embutido em Signature/KeyInfo/X509Certificate."""
    import base64

    from cryptography import x509
    from cryptography.x509.oid import NameOID

    nos = raiz.xpath(
        "//ds:X509Certificate/text()", namespaces={"ds": "http://www.w3.org/2000/09/xmldsig#"}
    )
    if not nos:
        return None
    try:
        cert = x509.load_der_x509_certificate(base64.b64decode(str(nos[0]).strip()))
    except Exception:
        return None
    atributos = {a.oid: a.value for a in cert.subject}
    return str(atributos.get(NameOID.COMMON_NAME, "")) or None


def verificar(xml: str | bytes, ca_pem_file: str | None = None) -> dict[str, str]:
    """Verifica a assinatura XMLDSig do XML (RSA-SHA1/SHA-1) e devolve o titular."""
    dados = xml.encode("utf-8") if isinstance(xml, str) else xml
    configuracao = SignatureConfiguration(
        require_x509=True,
        expect_references=1,
        signature_methods=frozenset({SignatureMethod.RSA_SHA1}),
        digest_algorithms=frozenset({DigestAlgorithm.SHA1}),
    )

    try:
        XMLVerifier().verify(dados, ca_pem_file=ca_pem_file, expect_config=configuracao)
    except Exception as exc:
        raise AssinaturaError(f"Assinatura invalida: {exc}") from exc

    raiz = etree.fromstring(dados)
    inf = raiz.find(f"{{{NAMESPACE_NFE}}}infNFe")
    return {
        "assinatura_valida": "true",
        "titular": _titular_do_xml(raiz) or "desconhecido",
        "chave": (inf.get("Id") or "").removeprefix("NFe") if inf is not None else "",
    }
