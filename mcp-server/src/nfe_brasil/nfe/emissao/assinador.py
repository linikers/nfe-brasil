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

from .certificado import CertificadoA1
from .chave import validar_chave

NAMESPACE_NFE = "http://www.portalfiscal.inf.br/nfe"
NAMESPACE_DSIG = "http://www.w3.org/2000/09/xmldsig#"


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
    # A NF-e exige a assinatura no namespace PADRAO, sem prefixo:
    # <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">. Com prefixo (ds:)
    # a SEFAZ devolve 587 "Usar somente o namespace padrao da NF-e".
    assinador.namespaces = {None: NAMESPACE_DSIG}  # type: ignore[dict-item]

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


def _c14n_isolado(elemento: etree._Element) -> bytes:
    """C14N 1.0 do elemento, isolado da arvore.

    Reparseia o fragmento para que as declaracoes de namespace venham no proprio
    elemento: canonizar uma sub-arvore que herda o namespace default do pai faz
    o lxml emitir `xmlns=""` espurio, o que nao corresponde ao que o validador
    da SEFAZ (Java/Xerces) calcula.
    """
    fragmento = etree.tostring(elemento)
    return bytes(
        etree.tostring(
            etree.fromstring(fragmento), method="c14n", exclusive=False, with_comments=False
        )
    )


def _titular_do_xml(raiz: etree._Element) -> str | None:
    """Le o CN do certificado embutido em Signature/KeyInfo/X509Certificate."""
    import base64

    from cryptography import x509
    from cryptography.x509.oid import NameOID

    nos = raiz.xpath(
        "//ds:X509Certificate/text()", namespaces={"ds": NAMESPACE_DSIG}
    )
    if not nos:
        return None
    try:
        cert = x509.load_der_x509_certificate(base64.b64decode(str(nos[0]).strip()))
    except Exception:
        return None
    atributos = {a.oid: a.value for a in cert.subject}
    return str(atributos.get(NameOID.COMMON_NAME, "")) or None


def verificar(xml: str | bytes) -> dict[str, str]:
    """Verifica a assinatura XMLDSig da NF-e de forma autocontida.

    Confere, com o certificado embutido no proprio XML:
      1. a assinatura RSA-SHA1 sobre o SignedInfo canonizado;
      2. o digest SHA-1 do elemento referenciado (o infNFe).

    Nao depende de cadeia de confianca externa — o certificado ICP-Brasil
    ja e validado pela SEFAZ na transmissao.
    """
    import base64
    import hashlib

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa

    dados = xml.encode("utf-8") if isinstance(xml, str) else xml
    raiz = etree.fromstring(dados)
    assinatura = raiz.find(f".//{{{NAMESPACE_DSIG}}}Signature")
    if assinatura is None:
        raise AssinaturaError("XML sem elemento Signature")

    cert_b64 = assinatura.find(f".//{{{NAMESPACE_DSIG}}}X509Certificate")
    if cert_b64 is None or not cert_b64.text:
        raise AssinaturaError("Signature sem certificado X509")
    certificado = x509.load_der_x509_certificate(base64.b64decode(cert_b64.text.strip()))

    # 1. assinatura sobre o SignedInfo
    signed_info = assinatura.find(f"{{{NAMESPACE_DSIG}}}SignedInfo")
    valor = assinatura.findtext(f"{{{NAMESPACE_DSIG}}}SignatureValue") or ""
    chave_publica = certificado.public_key()
    if not isinstance(chave_publica, rsa.RSAPublicKey):
        raise AssinaturaError("Certificado nao usa chave RSA")
    try:
        chave_publica.verify(
            base64.b64decode(valor.strip()),
            _c14n_isolado(signed_info),
            padding.PKCS1v15(),
            hashes.SHA1(),
        )
    except Exception as exc:
        raise AssinaturaError(f"Assinatura invalida: {exc}") from exc

    # 2. digest do elemento referenciado
    referencia = assinatura.find(f".//{{{NAMESPACE_DSIG}}}Reference")
    if referencia is None:
        raise AssinaturaError("Signature sem Reference")
    uri = (referencia.get("URI") or "").lstrip("#")
    alvo = raiz.find(f".//*[@Id='{uri}']")
    if alvo is None:
        raise AssinaturaError(f"Elemento referenciado nao encontrado: #{uri}")
    digest_esperado = base64.b64decode(
        referencia.findtext(f"{{{NAMESPACE_DSIG}}}DigestValue") or ""
    )
    if hashlib.sha1(_c14n_isolado(alvo)).digest() != digest_esperado:
        raise AssinaturaError("Digest do elemento referenciado diverge")

    return {
        "assinatura_valida": "true",
        "titular": _titular_do_xml(raiz) or "desconhecido",
        "chave": uri.removeprefix("NFe"),
    }
