"""DANFE NFC-e (modelo 65) — documento auxiliar em PDF.

O DANFE de NFC-e e um cupom de 80 mm (largura da bobina termica), com QR Code,
chave de acesso e protocolo de autorizacao. O modulo `danfe.py` deste pacote
cobre apenas NF-e modelo 55, por isso este caminho separado.

Fonte: leiaute 4.00 + Manual de Orientacao do Contribuinte (MOC), Anexo NFC-e.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path

import segno
from fpdf import FPDF
from lxml import etree

NS = {"n": "http://www.portalfiscal.inf.br/nfe"}

LARGURA_PAGINA = 80.0  # mm — bobina termica padrao
MARGEM = 3.0

FONTE_REGULAR = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FONTE_NEGRITO = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


class DanfeNfceError(ValueError):
    """XML nao permite montar o DANFE NFC-e."""


# --------------------------------------------------------------------------- #
# Formatacao de campos
# --------------------------------------------------------------------------- #


def _texto(raiz: etree._Element, caminho: str) -> str:
    valor = raiz.findtext(caminho, namespaces=NS)
    return (valor or "").strip()


def _moeda(valor: str | None) -> str:
    try:
        return f"{Decimal(valor or '0'):.2f}".replace(".", ",")
    except InvalidOperation:
        return "0,00"


def _quantidade(valor: str | None) -> str:
    try:
        return f"{Decimal(valor or '0'):.4f}".replace(".", ",")
    except InvalidOperation:
        return "0,0000"


def _data_hora(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return iso[:19].replace("T", " ")


def _formata_cnpj(cnpj: str | None) -> str:
    digitos = "".join(filter(str.isdigit, cnpj or ""))
    if len(digitos) != 14:
        return cnpj or ""
    return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"


def _formata_cep(cep: str | None) -> str:
    digitos = "".join(filter(str.isdigit, cep or ""))
    return f"{digitos[:5]}-{digitos[5:]}" if len(digitos) == 8 else (cep or "")


def _formata_fone(fone: str | None) -> str:
    d = "".join(filter(str.isdigit, fone or ""))
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    return fone or ""


def _chave_formatada(chave: str) -> list[str]:
    """Chave de acesso em blocos de 4 digitos (11 blocos, 2 linhas no cupom)."""
    grupos = [chave[i : i + 4] for i in range(0, len(chave), 4)]
    return [" ".join(grupos[:6]), " ".join(grupos[6:])]


def _forma_pagamento(codigo: str | None) -> str:
    return {
        "01": "DINHEIRO",
        "02": "CHEQUE",
        "03": "CARTAO DE CREDITO",
        "04": "CARTAO DE DEBITO",
        "05": "CREDITO LOJA",
        "15": "BOLETO",
        "17": "PIX",
        "99": "OUTROS",
    }.get((codigo or "").strip(), f"COD {codigo}")


# --------------------------------------------------------------------------- #
# Layout
# --------------------------------------------------------------------------- #


@dataclass
class _Linha:
    texto: str
    tamanho: float = 7.0
    negrito: bool = False
    alinhamento: str = "L"  # L | C | R
    espaco_antes: float = 0.0
    separador: bool = False


@dataclass
class _Cupom:
    linhas: list[_Linha] = field(default_factory=list)

    def add(self, texto: str, **kwargs: object) -> None:
        self.linhas.append(_Linha(texto=str(texto), **kwargs))  # type: ignore[arg-type]

    def regua(self) -> None:
        self.linhas.append(_Linha(texto="", separador=True))


def _quebrar(pdf: FPDF, texto: str, largura: float, tamanho: float, negrito: bool) -> list[str]:
    """Quebra o texto em linhas que caibam em `largura` mm."""
    pdf.set_font("DejaVu", "B" if negrito else "", tamanho)
    palavras = texto.split()
    if not palavras:
        return [""]
    linhas: list[str] = []
    atual = palavras[0]
    for palavra in palavras[1:]:
        tentativa = f"{atual} {palavra}"
        if pdf.get_string_width(tentativa) <= largura:
            atual = tentativa
        else:
            linhas.append(atual)
            atual = palavra
    linhas.append(atual)
    return linhas


def _altura_total(linhas_quebradas: list[tuple[_Linha, list[str]]]) -> float:
    altura = MARGEM * 2
    for linha, pedacos in linhas_quebradas:
        altura += linha.espaco_antes
        if linha.separador:
            altura += 1.5
            continue
        altura += len(pedacos) * (linha.tamanho * 0.42) + 0.6
    return altura


def _montar_conteudo(raiz: etree._Element) -> _Cupom:
    """Monta as linhas do cupom a partir do XML (nfeProc ou NFe)."""
    cupom = _Cupom()

    emit = raiz.find(".//n:emit", NS)
    if emit is None:
        raise DanfeNfceError("XML sem o grupo <emit>")

    end = emit.find("n:enderEmit", NS)
    ide = raiz.find(".//n:ide", NS)
    total = raiz.find(".//n:total/n:ICMSTot", NS)
    if ide is None or total is None:
        raise DanfeNfceError("XML sem <ide> ou <ICMSTot>")

    ambiente = _texto(raiz, ".//n:ide/n:tpAmb")

    # --- cabecalho do emitente
    cupom.add(_texto(emit, "n:xNome"), tamanho=8.5, negrito=True, alinhamento="C")
    cupom.add(
        f"CNPJ: {_formata_cnpj(_texto(emit, 'n:CNPJ'))}"
        + (f"  IE: {_texto(emit, 'n:IE')}" if _texto(emit, "n:IE") else ""),
        tamanho=6.8,
        alinhamento="C",
    )
    if end is not None:
        linha_end = " ".join(
            filter(
                None,
                [
                    _texto(end, "n:xLgr"),
                    _texto(end, "n:nro"),
                    _texto(end, "n:xBairro"),
                ],
            )
        )
        cupom.add(linha_end, tamanho=6.8, alinhamento="C")
        cupom.add(
            f"{_texto(end, 'n:xMun')}/{_texto(end, 'n:UF')}  CEP: {_formata_cep(_texto(end, 'n:CEP'))}",
            tamanho=6.8,
            alinhamento="C",
        )
        fone = _formata_fone(_texto(end, "n:fone"))
        if fone:
            cupom.add(f"FONE: {fone}", tamanho=6.8, alinhamento="C")
    cupom.regua()

    # --- titulo do documento
    cupom.add(
        "DANFE NFC-e - DOCUMENTO AUXILIAR DA NOTA FISCAL DE",
        tamanho=7.2,
        negrito=True,
        alinhamento="C",
    )
    cupom.add("CONSUMIDOR ELETRONICA", tamanho=7.2, negrito=True, alinhamento="C")
    cupom.add(
        "Nao permite aproveitamento de credito de ICMS", tamanho=6.2, alinhamento="C"
    )
    if ambiente == "2":
        cupom.add(
            "SEM VALOR FISCAL - AMBIENTE DE HOMOLOGACAO",
            tamanho=7.6,
            negrito=True,
            alinhamento="C",
            espaco_antes=1.5,
        )
    cupom.regua()

    # --- identificacao
    cupom.add(
        f"Nota {int(_texto(ide, 'n:nNF')) if _texto(ide, 'n:nNF').isdigit() else _texto(ide, 'n:nNF')}"
        f"  Serie {_texto(ide, 'n:serie')}  Modelo {_texto(ide, 'n:mod')}",
        tamanho=7.0,
        negrito=True,
    )
    cupom.add(f"Emissao: {_data_hora(_texto(ide, 'n:dhEmi'))}", tamanho=6.8)
    cupom.add(f"Natureza: {_texto(ide, 'n:natOp')}", tamanho=6.4)
    cupom.regua()

    # --- itens
    cupom.add("ITENS", tamanho=7.0, negrito=True)
    for det in raiz.findall(".//n:det", NS):
        prod = det.find("n:prod", NS)
        if prod is None:
            continue
        cupom.add(
            f"{det.get('nItem')}. {_texto(prod, 'n:xProd')}", tamanho=6.8, espaco_antes=1.0
        )
        cupom.add(
            f"   {_quantidade(_texto(prod, 'n:qCom'))} {_texto(prod, 'n:uCom')}"
            f" x {_moeda(_texto(prod, 'n:vUnCom'))}",
            tamanho=6.6,
        )
        cupom.add(f"   Total: R$ {_moeda(_texto(prod, 'n:vProd'))}", tamanho=6.6, alinhamento="R")
    cupom.regua()

    # --- totais
    cupom.add(f"TOTAL R$ {_moeda(_texto(total, 'n:vNF'))}", tamanho=9.5, negrito=True, alinhamento="C")
    if Decimal(_texto(total, "n:vDesc") or "0") > 0:
        cupom.add(f"Desconto R$ {_moeda(_texto(total, 'n:vDesc'))}", tamanho=6.6, alinhamento="C")
    cupom.regua()

    # --- pagamento
    cupom.add("PAGAMENTO", tamanho=7.0, negrito=True)
    for pag in raiz.findall(".//n:pag/n:detPag", NS):
        cupom.add(
            f"{_forma_pagamento(_texto(pag, 'n:tPag'))}  R$ {_moeda(_texto(pag, 'n:vPag'))}",
            tamanho=6.8,
        )
    cupom.regua()

    # --- consumidor
    dest = raiz.find(".//n:dest", NS)
    if dest is None:
        cupom.add("CONSUMIDOR NAO IDENTIFICADO", tamanho=6.8, alinhamento="C")
    else:
        doc = _texto(dest, "n:CPF") or _texto(dest, "n:CNPJ")
        cupom.add(
            f"{_texto(dest, 'n:xNome')} - {doc}", tamanho=6.8, alinhamento="C"
        )
    cupom.regua()

    # --- chave de acesso e protocolo
    chave = ""
    inf = raiz.find(".//n:infNFe", NS)
    if inf is not None:
        chave = (inf.get("Id") or "")[3:]
    cupom.add("CHAVE DE ACESSO", tamanho=6.6, negrito=True, alinhamento="C")
    if chave:
        for bloco in _chave_formatada(chave):
            cupom.add(bloco, tamanho=6.6, alinhamento="C")

    protocolo = _texto(raiz, ".//n:protNFe/n:infProt/n:nProt")
    if protocolo:
        cupom.add(
            f"Protocolo de autorizacao: {protocolo}",
            tamanho=6.2,
            alinhamento="C",
            espaco_antes=1.0,
        )
    cupom.add(
        "Consulte pela chave em www.fazenda.pr.gov.br/nfce/consulta",
        tamanho=6.0,
        alinhamento="C",
    )
    return cupom


def _renderizar(linhas: list[tuple[_Linha, list[str]]], qr_bytes: bytes) -> bytes:
    largura_util = LARGURA_PAGINA - 2 * MARGEM
    altura_qr = 30.0 if qr_bytes else 0.0
    altura = _altura_total(linhas) + (altura_qr + 3 if qr_bytes else 0)

    pdf = FPDF(unit="mm", format=(LARGURA_PAGINA, max(altura, 60.0)))
    pdf.set_margins(MARGEM, MARGEM, MARGEM)
    pdf.set_auto_page_break(False)
    pdf.add_font("DejaVu", "", str(FONTE_REGULAR))
    pdf.add_font("DejaVu", "B", str(FONTE_NEGRITO))
    pdf.add_page()

    for linha, pedacos in linhas:
        if linha.espaco_antes:
            pdf.ln(linha.espaco_antes)
        if linha.separador:
            y = pdf.get_y()
            pdf.set_draw_color(120, 120, 120)
            pdf.line(MARGEM, y + 0.6, LARGURA_PAGINA - MARGEM, y + 0.6)
            pdf.ln(1.5)
            continue
        pdf.set_font("DejaVu", "B" if linha.negrito else "", linha.tamanho)
        for pedaco in pedacos:
            pdf.cell(largura_util, linha.tamanho * 0.42 + 0.6, pedaco, align=linha.alinhamento)
            pdf.ln(linha.tamanho * 0.42 + 0.6)

    if qr_bytes:
        pdf.ln(2)
        pdf.image(BytesIO(qr_bytes), x=(LARGURA_PAGINA - altura_qr) / 2, w=altura_qr)

    saida = pdf.output()
    return bytes(saida)


def gerar_danfe_nfce(xml_content: str | bytes) -> bytes:
    """Gera o PDF do DANFE NFC-e (cupom 80 mm) a partir do XML autorizado.

    Aceita XML com ou sem o involucro <nfeProc>. O QR Code sai do proprio XML
    (grupo infNFeSupl) — sem ele, o cupom e gerado sem o codigo.
    """
    dados = xml_content.encode("utf-8") if isinstance(xml_content, str) else xml_content
    try:
        raiz = etree.fromstring(dados)
    except etree.XMLSyntaxError as exc:
        raise DanfeNfceError(f"XML invalido: {exc}") from exc

    if raiz.find(".//n:ide/n:mod", NS) is None:
        raise DanfeNfceError("XML nao parece ser de NF-e/NFC-e (sem <ide><mod>)")

    cupom = _montar_conteudo(raiz)

    # quebra as linhas medindo com as mesmas fontes do PDF final
    medidor = FPDF(unit="mm", format=(LARGURA_PAGINA, 100))
    medidor.add_font("DejaVu", "", str(FONTE_REGULAR))
    medidor.add_font("DejaVu", "B", str(FONTE_NEGRITO))
    largura_util = LARGURA_PAGINA - 2 * MARGEM
    linhas = [
        (
            linha,
            []
            if linha.separador
            else _quebrar(medidor, linha.texto, largura_util, linha.tamanho, linha.negrito),
        )
        for linha in cupom.linhas
    ]

    qr_conteudo = _texto(raiz, ".//n:infNFeSupl/n:qrCode")
    qr_bytes = b""
    if qr_conteudo:
        buffer = BytesIO()
        segno.make(qr_conteudo, error="m").save(buffer, kind="png", scale=6, border=1)
        qr_bytes = buffer.getvalue()

    return _renderizar(linhas, qr_bytes)
