"""Montagem do XML da NF-e/NFC-e (leiaute 4.00) a partir do payload.

Usa os bindings oficiais do pacote `nfelib` (gerados dos schemas da SEFAZ),
o que garante nomes e ordem dos campos conforme o leiaute.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from nfelib.nfe.bindings.v4_0.leiaute_nfe_v4_00 import (
    CofinsntCst,
    CofinsoutrCst,
    EmitCrt,
    Icmssn102Csosn,
    Icmssn500Csosn,
    PisntCst,
    PisoutrCst,
    TenderEmi,
    TinfRespTec,
    Tnfe,
)
from nfelib.nfe.bindings.v4_0.nfe_v4_00 import Nfe
from nfelib.nfe.bindings.v4_0.tipos_basico_v4_00 import Tamb, TcodUfIbge, Tmod, TufEmi
from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig

from .chave import montar_chave
from .schemas import DadosNota, Destinatario, Endereco, Item
from .transporte import url_consulta_chave, url_qrcode

NAMESPACE_NFE = "http://www.portalfiscal.inf.br/nfe"
_DSIG = "http://www.w3.org/2000/09/xmldsig#"


def _enm(classe: Any, valor: Any) -> Any:
    """Devolve o membro do enum xsdata correspondente a `valor`."""
    try:
        return classe(str(valor))
    except Exception:
        pass
    for membro in classe:
        if str(membro.value) == str(valor):
            return membro
    raise ValueError(f"Valor {valor!r} invalido para {classe.__name__}")


def _dec(valor: Decimal | str | float, casas: int = 2) -> str:
    """Formata decimal no padrao do leiaute (ponto, N casas)."""
    return f"{Decimal(str(valor)).quantize(Decimal('1.' + '0' * casas)):f}"


def _dh(quando: datetime) -> str:
    return quando.replace(microsecond=0).isoformat()


def _so_digitos(valor: str | None) -> str | None:
    if valor is None:
        return None
    limpo = "".join(filter(str.isdigit, valor))
    return limpo or None


def _endereco(ender: Endereco) -> TenderEmi:
    return TenderEmi(
        xLgr=ender.logradouro,
        nro=ender.numero,
        xCpl=ender.complemento,
        xBairro=ender.bairro,
        cMun=ender.codigo_municipio,
        xMun=ender.municipio,
        UF=_enm(TufEmi, ender.uf),
        CEP=_so_digitos(ender.cep),
        cPais="1058",
        xPais="BRASIL",
        fone=_so_digitos(ender.telefone),
    )


def obter_chave(dados: DadosNota) -> str:
    """Calcula a chave de acesso (44 digitos) da nota."""
    return montar_chave(
        codigo_uf=dados.codigo_uf,
        data_emissao=dados.emissao(),
        cnpj=dados.emitente.cnpj,
        modelo=dados.modelo,
        serie=dados.serie,
        numero=dados.numero,
        tipo_emissao=dados.tipo_emissao,
        codigo_numerico=dados.cnf(),
    )


def _grupo_icms(item: Item) -> Any:
    """Grupo ICMS: CSOSN para Simples Nacional, CST para Regime Normal."""
    if not item.csosn:
        raise ValueError(
            f"Item {item.codigo}: informe csosn (Simples Nacional). "
            "CST de ICMS para Regime Normal ainda nao implementado."
        )

    if item.csosn == "500":
        retido = item.valor_bc_st_retido is not None
        if retido:
            assert (
                item.percentual_st_retido is not None
                and item.valor_icms_st_retido is not None
            ), "grupo de ICMS-ST retido incompleto"
        grupo = Tnfe.InfNfe.Det.Imposto.Icms.Icmssn500(
            orig=item.origem,
            CSOSN=_enm(Icmssn500Csosn, item.csosn),
            vBCSTRet=(
                _dec(item.valor_bc_st_retido) if item.valor_bc_st_retido is not None else None
            ),
            pST=(
                _dec(item.percentual_st_retido, 4)
                if retido and item.percentual_st_retido is not None
                else None
            ),
            vICMSSTRet=(
                _dec(item.valor_icms_st_retido)
                if retido and item.valor_icms_st_retido is not None
                else None
            ),
        )
        return Tnfe.InfNfe.Det.Imposto.Icms(ICMSSN500=grupo)

    grupo = Tnfe.InfNfe.Det.Imposto.Icms.Icmssn102(
        orig=item.origem,
        CSOSN=_enm(Icmssn102Csosn, item.csosn),
    )
    return Tnfe.InfNfe.Det.Imposto.Icms(ICMSSN102=grupo)


# CST de PIS/COFINS nao tributado (grupo PISNT/COFINSNT).
_CST_NAO_TRIBUTADO = {"04", "05", "06", "07", "08", "09"}


def _grupo_pis(item: Item) -> Any:
    """PIS: CST 04-09 -> PISNT; demais (ex.: 49 no Simples Nacional) -> PISOutr zerado."""
    classe_pis = Tnfe.InfNfe.Det.Imposto.Pis
    if item.cst_pis in _CST_NAO_TRIBUTADO:
        return classe_pis(PISNT=classe_pis.Pisnt(CST=_enm(PisntCst, item.cst_pis)))
    return classe_pis(
        PISOutr=classe_pis.Pisoutr(
            CST=_enm(PisoutrCst, item.cst_pis), vBC="0.00", pPIS="0.00", vPIS="0.00"
        )
    )


def _grupo_cofins(item: Item) -> Any:
    """COFINS: CST 04-09 -> COFINSNT; demais -> COFINSOutr zerado."""
    classe_cofins = Tnfe.InfNfe.Det.Imposto.Cofins
    if item.cst_cofins in _CST_NAO_TRIBUTADO:
        return classe_cofins(
            COFINSNT=classe_cofins.Cofinsnt(CST=_enm(CofinsntCst, item.cst_cofins))
        )
    return classe_cofins(
        COFINSOutr=classe_cofins.Cofinsoutr(
            CST=_enm(CofinsoutrCst, item.cst_cofins), vBC="0.00", pCOFINS="0.00", vCOFINS="0.00"
        )
    )


def _grupo_imposto(item: Item) -> Any:
    return Tnfe.InfNfe.Det.Imposto(
        ICMS=_grupo_icms(item), PIS=_grupo_pis(item), COFINS=_grupo_cofins(item)
    )


def _destinatario(dest: Destinatario) -> Any:
    return Tnfe.InfNfe.Dest(
        CNPJ=dest.cnpj,
        CPF=dest.cpf,
        idEstrangeiro=dest.id_estrangeiro,
        xNome=dest.razao_social,
        enderDest=_endereco(dest.endereco) if dest.endereco else None,
        indIEDest=dest.indicador_ie,
        IE=dest.inscricao_estadual,
    )


def _item_det(item: Item, indice: int) -> Any:
    return Tnfe.InfNfe.Det(
        nItem=str(indice),
        prod=Tnfe.InfNfe.Det.Prod(
            cProd=item.codigo,
            cEAN=item.codigo_barras or "SEM GTIN",
            xProd=item.descricao,
            NCM=item.ncm,
            CEST=item.cest,
            CFOP=item.cfop,
            uCom=item.unidade,
            qCom=_dec(item.quantidade, 4),
            vUnCom=_dec(item.valor_unitario, 10),
            vProd=_dec(item.valor_total),
            cEANTrib=item.codigo_barras or "SEM GTIN",
            uTrib=item.unidade,
            qTrib=_dec(item.quantidade, 4),
            vUnTrib=_dec(item.valor_unitario, 10),
            indTot="1",
        ),
        imposto=_grupo_imposto(item),
        infAdProd=item.info_adicional,
    )


def _responsavel_tecnico(rt: Any) -> TinfRespTec | None:
    """Grupo infRespTec — exigido quando procEmi=0 (rejeicao 972 sem ele)."""
    if rt is None:
        return None
    return TinfRespTec(
        CNPJ=rt.cnpj,
        xContato=rt.contato,
        email=rt.email,
        fone=_so_digitos(rt.fone),
        idCSRT=rt.id_csrt,
        hashCSRT=rt.hash_csrt,
    )


def _inf_nfe_supl(dados: DadosNota, chave: str, uf: str = "PR") -> Any:
    """Grupo infNFeSupl da NFC-e (QR Code + URL de consulta).

    QR Code versao 3 ONLINE: <url>?p=<chave>|<versao>|<tpAmb>.
    A partir da NT 2025.001 o CSC deixou de ser necessario.
    """
    if dados.modelo != "65":
        return None

    url = dados.url_qrcode or url_qrcode(uf, dados.modelo)
    if not url:
        raise ValueError(f"URL de consulta do QR Code nao configurada para a UF {uf}")

    url_chave = dados.url_consulta_chave or url_consulta_chave(uf, dados.modelo)
    if not url_chave:
        raise ValueError(f"URL de consulta por chave nao configurada para a UF {uf}")

    return Tnfe.InfNfeSupl(
        qrCode=f"{url}?p={chave}|{dados.versao_qrcode}|{dados.ambiente}",
        urlChave=url_chave,
    )


def construir_tnfe(dados: DadosNota, chave: str, uf: str = "PR") -> Nfe:
    """Monta o objeto Nfe (sem assinatura) para a chave informada."""
    emitente = dados.emitente

    ide = Tnfe.InfNfe.Ide(
        cUF=_enm(TcodUfIbge, dados.codigo_uf),
        cNF=chave[35:43],
        natOp=dados.natureza_operacao,
        mod=_enm(Tmod, dados.modelo),
        serie=dados.serie,
        nNF=dados.numero,
        dhEmi=_dh(dados.emissao()),
        tpNF=dados.tipo_documento,
        idDest=dados.destino_operacao,
        cMunFG=dados.codigo_municipio_fato_gerador,
        tpImp=dados.impressao(),
        tpEmis=dados.tipo_emissao,
        cDV=chave[43:44],
        tpAmb=_enm(Tamb, dados.ambiente),
        finNFe=dados.finalidade,
        indFinal="1" if dados.consumidor_final else "0",
        indPres=dados.indicador_presenca,
        procEmi=dados.processamento,
        verProc=dados.versao_aplicativo,
    )

    emit = Tnfe.InfNfe.Emit(
        CNPJ=emitente.cnpj,
        xNome=emitente.razao_social,
        xFant=emitente.nome_fantasia,
        enderEmit=_endereco(emitente.endereco),
        IE=emitente.inscricao_estadual,
        # O schema pos IM e CNAE na mesma sequencia opcional: informar CNAE exige IM.
        IM=emitente.inscricao_municipal,
        CNAE=_so_digitos(emitente.cnae) if emitente.inscricao_municipal else None,
        CRT=_enm(EmitCrt, emitente.crt),
    )

    itens = dados.itens
    base_st_retido = sum((i.valor_bc_st_retido or Decimal("0.00") for i in itens), Decimal("0.00"))
    icms_st_retido = sum((i.valor_icms_st_retido or Decimal("0.00") for i in itens), Decimal("0.00"))

    icms_tot = Tnfe.InfNfe.Total.Icmstot(
        vBC="0.00",
        vICMS="0.00",
        vICMSDeson="0.00",
        vFCPUFDest="0.00",
        vICMSUFDest="0.00",
        vICMSUFRemet="0.00",
        vFCP="0.00",
        vBCST="0.00",
        vST="0.00",
        vFCPST="0.00",
        vFCPSTRet="0.00",
        vProd=_dec(dados.valor_total),
        vFrete="0.00",
        vSeg="0.00",
        vDesc="0.00",
        vII="0.00",
        vIPI="0.00",
        vIPIDevol="0.00",
        vPIS="0.00",
        vCOFINS="0.00",
        vOutro="0.00",
        vNF=_dec(dados.valor_total),
    )
    if base_st_retido or icms_st_retido:
        icms_tot.vBCSTRet = _dec(base_st_retido)
        icms_tot.vICMSSTRet = _dec(icms_st_retido)

    inf_nfe = Tnfe.InfNfe(
        ide=ide,
        emit=emit,
        dest=_destinatario(dados.destinatario) if dados.destinatario else None,
        det=[_item_det(item, indice) for indice, item in enumerate(itens, start=1)],
        total=Tnfe.InfNfe.Total(ICMSTot=icms_tot),
        transp=Tnfe.InfNfe.Transp(modFrete=dados.modalidade_frete),
        pag=Tnfe.InfNfe.Pag(
            detPag=[
                Tnfe.InfNfe.Pag.DetPag(tPag=p.forma, vPag=_dec(p.valor))
                for p in dados.pagamentos
            ]
        ),
        infAdic=Tnfe.InfNfe.InfAdic(infCpl=dados.observacoes)
        if dados.observacoes
        else None,
        infRespTec=_responsavel_tecnico(dados.responsavel_tecnico),
        versao="4.00",
        Id=f"NFe{chave}",
    )
    return Nfe(infNFe=inf_nfe, infNFeSupl=_inf_nfe_supl(dados, chave, uf))


def serializar(objeto: Any) -> str:
    """Serializa um dataclass xsdata do nfelib no XML do leiaute."""
    serializador = XmlSerializer(config=SerializerConfig(indent=None))
    return serializador.render(obj=objeto, ns_map={None: NAMESPACE_NFE})


def montar_xml(dados: DadosNota, tnfe: Any) -> str:
    """Serializa o Nfe no XML do leiaute (sem assinatura)."""
    return serializar(tnfe)


def sem_assinatura(xml: str) -> str:
    """Remove o elemento Signature e o namespace dsig nao utilizado."""
    return xml


__all__ = [
    "NAMESPACE_NFE",
    "construir_tnfe",
    "montar_xml",
    "obter_chave",
    "serializar",
]
