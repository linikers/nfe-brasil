"""Testes do emissor de NF-e/NFC-e (leiaute 4.00).

Cobrem: montagem da chave de acesso, montagem do XML validada contra o schema
oficial da SEFAZ, assinatura XMLDSig (RSA-SHA1/SHA-1) e regras de campos que o
schema trata como obrigatorios em conjunto.
"""

from __future__ import annotations

import ssl
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import nfelib
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from lxml import etree

from nfe_brasil.nfe.emissao import (
    CertificadoA1,
    DadosNota,
    Destinatario,
    Emitente,
    Endereco,
    Item,
    Pagamento,
    ResponsavelTecnico,
    assinar,
    construir_tnfe,
    montar_pacote,
    obter_chave,
    serializar,
    validar_chave,
    verificar,
)
from nfe_brasil.nfe.emissao.chave import ChaveInvalidaError, calcular_dv
from nfe_brasil.nfe.emissao.transporte import (
    Servico,
    _corpo_resposta,
    contexto_tls,
    endpoint,
)

ESQUEMAS = Path(nfelib.__file__ or "").parent / "nfe" / "schemas" / "v4_0"


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


def _chave_rsa() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _gerar_cadeia(diretorio: Path) -> tuple[Path, Path]:
    """Gera CA raiz + folha com CN=razao social:CNPJ e devolve (pfx, ca.pem)."""
    agora = datetime.now(timezone.utc)

    ca_chave = _chave_rsa()
    ca_nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "AC TESTE NF-E")])
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_nome)
        .issuer_name(ca_nome)
        .public_key(ca_chave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - timedelta(days=1))
        .not_valid_after(agora + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_chave, hashes.SHA256())
    )

    chave = _chave_rsa()
    cnpj = "11222333000181"
    sujeito = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "LANCHONETE EXEMPLO LTDA."),
            x509.NameAttribute(
                NameOID.COMMON_NAME, f"LANCHONETE EXEMPLO LTDA.:{cnpj}"
            ),
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(sujeito)
        .issuer_name(ca_nome)
        .public_key(chave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - timedelta(days=1))
        .not_valid_after(agora + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=True,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
        .sign(ca_chave, hashes.SHA256())
    )

    pfx = diretorio / "teste.pfx"
    pfx.write_bytes(
        pkcs12.serialize_key_and_certificates(
            name=b"LANCHONETE EXEMPLO",
            key=chave,
            cert=cert,
            cas=[ca_cert],
            encryption_algorithm=serialization.BestAvailableEncryption(b"123456"),
        )
    )
    ca_pem = diretorio / "teste.ca.pem"
    ca_pem.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
    return pfx, ca_pem


@pytest.fixture(scope="module")
def cadeia_certificado(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    return _gerar_cadeia(tmp_path_factory.mktemp("certs"))


@pytest.fixture(scope="module")
def certificado(cadeia_certificado: tuple[Path, Path]) -> CertificadoA1:
    return CertificadoA1(cadeia_certificado[0], "123456")


@pytest.fixture
def emitente() -> Emitente:
    return Emitente(
        cnpj="11222333000181",
        razao_social="LANCHONETE EXEMPLO LTDA.",
        inscricao_estadual="1000000000",
        cnae="5611203",
        crt="1",
        endereco=Endereco(
            logradouro="CERRO AZUL",
            numero="2207",
            bairro="VILA MARUMBY",
            codigo_municipio="4115200",
            municipio="MARINGA",
            uf="PR",
            cep="87005260",
            telefone="4432288785",
        ),
    )


@pytest.fixture
def item() -> Item:
    return Item(
        codigo="REF-COCA-350",
        descricao="REFRIGERANTE COCA-COLA 350ML",
        ncm="22021000",
        cfop="5405",
        quantidade=Decimal("2"),
        valor_unitario=Decimal("5.00"),
        csosn="500",
    )


def _dados(emitente: Emitente, item: Item, *, modelo: str, com_destinatario: bool) -> DadosNota:
    return DadosNota(
        modelo=modelo,  # type: ignore[arg-type]
        serie="1",
        numero="1",
        ambiente="2",
        natureza_operacao="Venda de mercadoria",
        codigo_uf="41",
        codigo_municipio_fato_gerador="4115200",
        emitente=emitente,
        destinatario=(
            Destinatario(cpf="52998224725", razao_social="CONSUMIDOR TESTE", indicador_ie="9")
            if com_destinatario
            else None
        ),
        itens=[item],
        pagamentos=[Pagamento(forma="01", valor=Decimal("10.00"))],
        data_emissao=datetime(2026, 10, 16, 10, 30, tzinfo=timezone(timedelta(hours=-3))),
        codigo_numerico="12345678",
    )


def _validar(xml: str, arquivo_xsd: str) -> list[str]:
    esquema = etree.XMLSchema(etree.parse(str(ESQUEMAS / arquivo_xsd)))
    if esquema.validate(etree.fromstring(xml.encode())):
        return []
    return [f"linha {erro.line}: {erro.message}" for erro in esquema.error_log]


# --------------------------------------------------------------------------- #
# Chave de acesso
# --------------------------------------------------------------------------- #


def test_chave_tem_44_digitos_e_dv_calculado() -> None:
    chave = "41261011222333000181650010000000011123456780"
    campos = validar_chave(chave)

    assert len(chave) == 44
    assert campos["codigo_uf"] == "41"
    assert campos["cnpj_emitente"] == "11222333000181"
    assert campos["modelo"] == "65"
    assert campos["numero"] == "000000001"
    assert calcular_dv(chave[:43]) == chave[43]


def test_chave_com_dv_errado_e_rejeitada() -> None:
    with pytest.raises(ChaveInvalidaError):
        validar_chave("41261011222333000181650010000000011123456781")


# --------------------------------------------------------------------------- #
# Montagem e validação no schema oficial
# --------------------------------------------------------------------------- #


def test_nfce_sem_destinatario_e_valida_no_xsd(
    emitente: Emitente, item: Item, certificado: CertificadoA1, cadeia_certificado: tuple[Path, Path]
) -> None:
    dados = _dados(emitente, item, modelo="65", com_destinatario=False)
    chave = obter_chave(dados)
    xml = serializar(construir_tnfe(dados, chave))
    assinado = assinar(xml, certificado, chave=chave)

    assert _validar(assinado, "nfe_v4.00.xsd") == []
    assert "<dest>" not in assinado
    assert assinado.count("</Signature>") == 1
    # a assinatura vai no namespace padrao (sem prefixo ds:) — exigencia da SEFAZ (cStat 587)
    assert '<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">' in assinado
    assert "ds:Signature" not in assinado

    resultado = verificar(assinado)
    assert resultado["assinatura_valida"] == "true"
    assert resultado["titular"] == "LANCHONETE EXEMPLO LTDA.:11222333000181"
    assert resultado["chave"] == chave


def test_nfe_com_destinatario_e_valida_no_xsd(
    emitente: Emitente, item: Item, certificado: CertificadoA1, cadeia_certificado: tuple[Path, Path]
) -> None:
    dados = _dados(emitente, item, modelo="55", com_destinatario=True)
    chave = obter_chave(dados)
    assinado = assinar(serializar(construir_tnfe(dados, chave)), certificado, chave=chave)

    assert _validar(assinado, "nfe_v4.00.xsd") == []
    assert "<dest><CPF>52998224725</CPF>" in assinado
    assert verificar(assinado)["assinatura_valida"] == "true"


def test_nfe_55_sem_destinatario_omite_o_grupo(emitente: Emitente, item: Item) -> None:
    """O schema aceita omitir <dest>, mas a SEFAZ rejeita NF-e 55 assim (regra E01-10, erro 719).

    Por isso a NFC-e (modelo 65) e o documento correto para consumidor nao identificado.
    """
    dados = _dados(emitente, item, modelo="55", com_destinatario=False)
    xml = serializar(construir_tnfe(dados, obter_chave(dados)))

    dados_nfce = _dados(emitente, item, modelo="65", com_destinatario=False)
    xml_nfce = serializar(construir_tnfe(dados_nfce, obter_chave(dados_nfce)))

    assert "<dest>" not in xml
    assert "<dest>" not in xml_nfce
    assert "<mod>55</mod>" in xml
    assert "<mod>65</mod>" in xml_nfce


def test_envelope_do_lote_e_valido_no_xsd(
    emitente: Emitente, item: Item, certificado: CertificadoA1
) -> None:
    dados = _dados(emitente, item, modelo="65", com_destinatario=False)
    _, xml_nfe, xml_envi = montar_pacote(dados, certificado)

    assert xml_envi.startswith('<enviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">')
    assert "<idLote>" in xml_envi
    assert "<indSinc>1</indSinc>" in xml_envi
    assert xml_nfe in xml_envi
    assert _validar(xml_envi, "enviNFe_v4.00.xsd") == []


def test_nfce_tem_qrcode_v3_e_valida_no_xsd(
    emitente: Emitente, item: Item, certificado: CertificadoA1
) -> None:
    """NFC-e exige o grupo infNFeSupl com o QR Code (sem ele, rejeicao 394)."""
    dados = _dados(emitente, item, modelo="65", com_destinatario=False)
    chave = obter_chave(dados)
    assinado = assinar(serializar(construir_tnfe(dados, chave)), certificado, chave=chave)

    esperado = f"http://www.fazenda.pr.gov.br/nfce/qrcode?p={chave}|3|2"
    assert f"<qrCode>{esperado}</qrCode>" in assinado
    assert "<urlChave>http://www.fazenda.pr.gov.br/nfce/consulta</urlChave>" in assinado
    # O XSD valida o padrao do QR Code (v3 online) contra o schema oficial
    assert _validar(assinado, "nfe_v4.00.xsd") == []


def test_nfe_55_nao_leva_o_grupo_infnfesupl(emitente: Emitente, item: Item) -> None:
    """NF-e modelo 55 com infNFeSupl e rejeitada (rejeicao 393)."""
    dados = _dados(emitente, item, modelo="55", com_destinatario=True)
    xml = serializar(construir_tnfe(dados, obter_chave(dados)))

    assert "infNFeSupl" not in xml
    assert "qrCode" not in xml


def test_endpoint_separa_nfe_de_nfce() -> None:
    """No PR a NFC-e usa host proprio (nfce.sefa.pr.gov.br), diferente da NF-e."""
    assert (
        endpoint(Servico.AUTORIZACAO, "2", "PR", "65")
        == "https://homologacao.nfce.sefa.pr.gov.br/nfce/NFeAutorizacao4"
    )
    assert (
        endpoint(Servico.AUTORIZACAO, "1", "PR", "55")
        == "https://nfe.sefa.pr.gov.br/nfe/NFeAutorizacao4"
    )


def test_pacote_assinado_nao_transmite_por_padrao(
    emitente: Emitente, item: Item, certificado: CertificadoA1
) -> None:
    dados = _dados(emitente, item, modelo="65", com_destinatario=False)
    chave, _, xml_envi = montar_pacote(dados, certificado)

    assert chave == obter_chave(dados)
    assert "<NFe xmlns=" in xml_envi
    assert '<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">' in xml_envi


# --------------------------------------------------------------------------- #
# Regras que o schema impõe em conjunto
# --------------------------------------------------------------------------- #


def test_grupo_icms_st_incompleto_e_rejeitado(item: Item) -> None:
    campos = item.model_dump()
    campos["valor_bc_st_retido"] = Decimal("10.00")  # sem pST e sem valor do ICMS-ST

    with pytest.raises(ValueError, match="ICMS-ST retido"):
        Item(**campos)


def test_cnae_so_e_emitido_com_inscricao_municipal(
    emitente: Emitente, item: Item
) -> None:
    dados = _dados(emitente, item, modelo="65", com_destinatario=False)
    assert "<CNAE>" not in serializar(construir_tnfe(dados, obter_chave(dados)))

    emitente_com_im = emitente.model_copy(update={"inscricao_municipal": "123456"})
    dados_im = _dados(emitente_com_im, item, modelo="65", com_destinatario=False)
    xml = serializar(construir_tnfe(dados_im, obter_chave(dados_im)))

    assert "<IM>123456</IM><CNAE>5611203</CNAE>" in xml


def test_total_da_nota_soma_os_itens(emitente: Emitente, item: Item) -> None:
    dados = _dados(emitente, item, modelo="65", com_destinatario=False)
    xml = serializar(construir_tnfe(dados, obter_chave(dados)))

    assert dados.valor_total == Decimal("10.00")
    assert "<vProd>10.00</vProd>" in xml
    assert "<vNF>10.00</vNF>" in xml
    assert '<qCom>2.0000</qCom>' in xml
    assert "<vUnCom>5.0000000000</vUnCom>" in xml


# --------------------------------------------------------------------------- #
# Regras descobertas transmitindo de verdade para a SEFAZ-PR (homologacao)
# --------------------------------------------------------------------------- #


def test_tls_fixado_em_1_2() -> None:
    """SEFAZ-PR nao completa o handshake em TLS 1.3 (handshake failure / bad certificate)."""
    contexto = contexto_tls()

    assert contexto.minimum_version == ssl.TLSVersion.TLSv1_2
    assert contexto.maximum_version == ssl.TLSVersion.TLSv1_2


def test_corpo_resposta_extrai_o_documento_e_nao_o_envelope() -> None:
    """A resposta vem embrulhada em soap:Body/nfeResultMsg; o parser quer o retEnviNFe."""
    resposta = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"><soap:Body>'
        '<nfeResultMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4">'
        '<retEnviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">'
        "<cStat>100</cStat><xMotivo>Autorizado o uso da NF-e</xMotivo>"
        "</retEnviNFe></nfeResultMsg></soap:Body></soap:Envelope>"
    )

    extraido = _corpo_resposta(resposta)

    assert extraido.startswith("<retEnviNFe")
    assert "nfeResultMsg" not in extraido
    assert "<cStat>100</cStat>" in extraido


def test_responsavel_tecnico_entra_no_xml_e_valida_no_xsd(
    emitente: Emitente, item: Item, certificado: CertificadoA1
) -> None:
    """Sem infRespTec a SEFAZ devolve 972; o grupo precisa dos 4 campos."""
    dados = _dados(emitente, item, modelo="65", com_destinatario=False).model_copy(
        update={
            "responsavel_tecnico": ResponsavelTecnico(
                cnpj="11222333000181",
                contato="CONTATO TECNICO",
                email="tecnico@exemplo.com.br",
                fone="(44) 3228-8785",
            )
        }
    )
    chave = obter_chave(dados)
    xml = assinar(serializar(construir_tnfe(dados, chave)), certificado, chave=chave)

    assert _validar(xml, "nfe_v4.00.xsd") == []
    assert "<infRespTec>" in xml
    assert "<xContato>CONTATO TECNICO</xContato>" in xml
    assert "<email>tecnico@exemplo.com.br</email>" in xml
    # fone sai so com digitos, conforme o leiaute
    assert "<fone>4432288785</fone>" in xml
    # idCSRT/hashCSRT so vao quando a UF exige o CSRT
    assert "idCSRT" not in xml


def test_sem_responsavel_tecnico_o_grupo_e_omitido(
    emitente: Emitente, item: Item, certificado: CertificadoA1
) -> None:
    dados = _dados(emitente, item, modelo="65", com_destinatario=False)
    chave = obter_chave(dados)
    xml = assinar(serializar(construir_tnfe(dados, chave)), certificado, chave=chave)

    assert _validar(xml, "nfe_v4.00.xsd") == []
    assert "infRespTec" not in xml


def test_csrt_entra_quando_informado(emitente: Emitente, item: Item) -> None:
    dados = _dados(emitente, item, modelo="65", com_destinatario=False).model_copy(
        update={
            "responsavel_tecnico": ResponsavelTecnico(
                cnpj="11222333000181",
                contato="CONTATO TECNICO",
                email="tecnico@exemplo.com.br",
                fone="4432288785",
                id_csrt="000001",
                hash_csrt="ABCDEF0123456789ABCDEF0123456789ABCDEF01",
            )
        }
    )
    xml = serializar(construir_tnfe(dados, obter_chave(dados)))

    assert "<idCSRT>000001</idCSRT>" in xml
    assert "<hashCSRT>" in xml
