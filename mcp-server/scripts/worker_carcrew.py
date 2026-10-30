#!/usr/bin/env python3
"""Worker de emissão NF-e (modelo 55) do CarCrew Commerce.

Fluxo:
  1. puxa as notas `pronta` do site  (GET /api/fiscal/pendentes, Bearer)
  2. monta o `DadosNota` (IBGE por CEP, CPF/CNPJ, destino, presença, frete)
  3. F1: `montar_pacote()` — assina e salva o XML, SEM transmitir
     F2: `emitir()` — transmite, trata recibo assíncrono e devolve ao site
  4. devolve o resultado em POST /api/fiscal/retorno

O site não emite: quem fala com a SEFAZ é este processo. Ele precisa rodar num
servidor com o certificado A1 da empresa — não em serverless.

Variáveis de ambiente:
  CARCREW_SITE           ex. https://carcrew.com.br
  CARCREW_CHAVE          chave de API criada em Fiscal → Notas fiscais
  CARCREW_PFX            caminho do .pfx
  CARCREW_PFX_SENHA      senha do .pfx
  CARCREW_UF             UF do emitente (default PR)
  CARCREW_RESP_CNPJ      CNPJ do responsável técnico (infRespTec, evita 972)
  CARCREW_RESP_CONTATO / CARCREW_RESP_EMAIL / CARCREW_RESP_FONE

Uso:
  python worker_carcrew.py                 # F1: assina e salva
  python worker_carcrew.py --transmitir    # F2: transmite em homologação
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import httpx

from nfe_brasil.nfe.emissao import (
    CertificadoA1,
    DadosNota,
    Destinatario,
    Emitente,
    Endereco,
    Item,
    Pagamento,
    ResponsavelTecnico,
    consultar_recibo,
    emitir,
    montar_pacote,
)
from nfe_brasil.nfe.emissao.helpers import (
    destino_operacao,
    indicador_presenca,
    modalidade_frete,
    resolver_ibge,
    tipo_documento,
)

SAIDA = Path(os.environ.get("CARCREW_SAIDA", "./xml-saida"))
NUMERACAO = Path(os.environ.get("CARCREW_NUMERACAO", "./numeracao.json"))


def env(nome: str, padrao: str | None = None) -> str:
    valor = os.environ.get(nome, padrao)
    if not valor:
        sys.exit(f"[erro] variável {nome} não definida")
    return valor


def puxar_pendentes(site: str, chave: str, dias: int) -> list[dict]:
    fim = datetime.now()
    inicio = fim.replace(hour=0, minute=0, second=0, microsecond=0)
    params = {"de": inicio.date().isoformat(), "ate": fim.date().isoformat()}
    resposta = httpx.get(
        f"{site.rstrip('/')}/api/fiscal/pendentes",
        params=params,
        headers={"Authorization": f"Bearer {chave}"},
        timeout=30,
    )
    resposta.raise_for_status()
    dados = resposta.json()
    return dados.get("pacote", [])


def proximo_numero(serie: str) -> str:
    estado = {"serie": serie, "proximo": 1}
    if NUMERACAO.exists():
        estado.update(json.loads(NUMERACAO.read_text()))
    numero = int(estado["proximo"])
    estado["proximo"] = numero + 1
    NUMERACAO.write_text(json.dumps(estado, indent=2))
    return str(numero)


def devolver(site: str, chave: str, pedido_id: str, payload: dict) -> None:
    resposta = httpx.post(
        f"{site.rstrip('/')}/api/fiscal/retorno",
        json={"pedidoId": pedido_id, **payload},
        headers={"Authorization": f"Bearer {chave}"},
        timeout=30,
    )
    if resposta.status_code >= 400:
        print(f"  [aviso] retorno recusado pelo site: {resposta.status_code} {resposta.text[:120]}")


def montar_dados(nota: dict, numero: str, serie: str, uf: str, ambiente: str) -> DadosNota:
    emitente = nota["emitente"]
    dest = nota["destinatario"]
    endereco = dest["endereco"]

    ibge = endereco.get("codigoMunicipio") or resolver_ibge(endereco.get("cep"))
    if not ibge:
        raise ValueError("não foi possível resolver o código IBGE do município (CEP)")

    tipo, digitos = tipo_documento(dest.get("documento"))
    if tipo is None:
        raise ValueError("destinatário sem CPF/CNPJ válido")

    resp_tecnico = None
    if os.environ.get("CARCREW_RESP_CNPJ"):
        resp_tecnico = ResponsavelTecnico(
            cnpj=os.environ["CARCREW_RESP_CNPJ"],
            contato=env("CARCREW_RESP_CONTATO", "Suporte"),
            email=env("CARCREW_RESP_EMAIL", "suporte@localhost"),
            fone=env("CARCREW_RESP_FONE", "4400000000"),
        )

    return DadosNota(
        modelo="55",
        serie=serie,
        numero=numero,
        ambiente=ambiente,  # type: ignore[arg-type]
        codigo_uf=str(nota["emitente"].get("uf") and _codigo_uf(nota["emitente"]["uf"])),
        codigo_municipio_fato_gerador=ibge if nota["emitente"].get("uf") else ibge,
        emitente=Emitente(
            cnpj=emitente["cnpj"],
            razao_social=emitente["razaoSocial"],
            inscricao_estadual=emitente.get("ie") or "",
            endereco=Endereco(
                logradouro="ENDERECO DO EMITENTE",
                numero="S/N",
                bairro="CENTRO",
                codigo_municipio=ibge,
                municipio="MARINGA",
                uf=uf,
                cep="87000000",
            ),
        ),
        destinatario=Destinatario(
            cpf=digitos if tipo == "cpf" else None,
            cnpj=digitos if tipo == "cnpj" else None,
            razao_social=(dest.get("nome") or "CONSUMIDOR")[:60],
            endereco=Endereco(
                logradouro=(endereco.get("logradouro") or "")[:60] or "NAO INFORMADO",
                numero=endereco.get("numero") or "S/N",
                bairro=(endereco.get("bairro") or "CENTRO")[:60],
                codigo_municipio=ibge,
                municipio=(endereco.get("cidade") or "MARINGA")[:60],
                uf=(endereco.get("uf") or uf)[:2],
                cep=endereco.get("cep") or "",
            ),
        ),
        itens=[
            Item(
                codigo=(i.get("sku") or str(idx))[:60],
                descricao=(i["nome"] or "ITEM")[:120],
                ncm=(i.get("ncm") or "").replace(".", ""),
                cfop=i.get("cfop") or "5102",
                unidade=i.get("unidade") or "UN",
                quantidade=i["quantidade"],
                valor_unitario=i["valorUnitario"],
                csosn=i.get("cst") or "102",
            )
            for idx, i in enumerate(nota["itens"], start=1)
        ],
        pagamentos=[Pagamento(forma=nota["pagamento"]["forma"], valor=nota["pagamento"]["valor"])],
        responsavel_tecnico=resp_tecnico,
        destino_operacao=destino_operacao(endereco.get("uf"), uf),
        indicador_presenca=indicador_presenca(nota.get("canal")),
        modalidade_frete=modalidade_frete(nota.get("frete")),
        observacoes=nota.get("observacoes"),
    )


def _codigo_uf(uf: str) -> str:
    """Código IBGE da UF (2 dígitos) — o leiaute pede número, não sigla."""
    tabela = {
        "AC": "12", "AL": "27", "AP": "16", "AM": "13", "BA": "29", "CE": "23",
        "DF": "53", "ES": "32", "GO": "52", "MA": "21", "MT": "51", "MS": "50",
        "MG": "31", "PA": "15", "PB": "25", "PR": "41", "PE": "26", "PI": "22",
        "RJ": "33", "RN": "24", "RS": "43", "RO": "11", "RR": "14", "SC": "42",
        "SP": "35", "SE": "28", "TO": "17",
    }
    return tabela.get(uf.upper(), "41")


def main() -> int:
    parser = argparse.ArgumentParser(description="Worker de emissão NF-e 55 (CarCrew)")
    parser.add_argument("--transmitir", action="store_true", help="F2: transmite para a SEFAZ")
    parser.add_argument("--producao", action="store_true", help="usa tpAmb=1 (valor fiscal real)")
    parser.add_argument("--serie", default=os.environ.get("CARCREW_SERIE", "1"))
    args = parser.parse_args()

    site = env("CARCREW_SITE")
    chave = env("CARCREW_CHAVE")
    uf = os.environ.get("CARCREW_UF", "PR")
    ambiente = "1" if args.producao else "2"

    certificado = CertificadoA1(env("CARCREW_PFX"), env("CARCREW_PFX_SENHA"))
    notas = puxar_pendentes(site, chave, dias=30)
    print(f"[worker] {len(notas)} nota(s) na fila · ambiente={'producao' if ambiente == '1' else 'homologacao'}")

    SAIDA.mkdir(parents=True, exist_ok=True)
    falhas = 0

    for nota in notas:
        numero = proximo_numero(args.serie)
        try:
            dados = montar_dados(nota, numero, args.serie, uf, ambiente)

            if not args.transmitir:
                chave_nfe, xml_assinado, _ = montar_pacote(dados, certificado, uf)
                arquivo = SAIDA / f"{chave_nfe}.xml"
                arquivo.write_text(xml_assinado, encoding="utf-8")
                print(f"  [F1] pedido {nota['pedidoId'][-8:]} assinado · chave {chave_nfe} · {arquivo}")
                continue

            resultado = emitir(dados, certificado, enviar_de_verdade=True, uf=uf)
            print(f"  [F2] pedido {nota['pedidoId'][-8:]} · cStat {resultado.codigo_status} · {resultado.motivo}")

            if resultado.codigo_status == "103":  # lote recebido: consulta o recibo
                recibo = consultar_recibo(resultado.recibo or "", modelo="55", ambiente=ambiente, uf=uf)  # type: ignore[arg-type]
                print(f"       recibo: {recibo.codigo_status} {recibo.motivo}")

            if resultado.codigo_status == "100":
                devolver(site, chave, nota["pedidoId"], {
                    "status": "autorizada",
                    "numero": numero,
                    "serie": args.serie,
                    "chave": resultado.chave,
                })
            else:
                devolver(site, chave, nota["pedidoId"], {
                    "status": "rejeitada",
                    "motivo": f"{resultado.codigo_status}: {resultado.motivo}"[:200],
                })
                falhas += 1
        except Exception as erro:  # noqa: BLE001 - uma nota com erro não derruba o lote
            falhas += 1
            print(f"  [erro] pedido {nota['pedidoId'][-8:]}: {erro}")
            if args.transmitir:
                devolver(site, chave, nota["pedidoId"], {
                    "status": "rejeitada",
                    "motivo": str(erro)[:200],
                })

    print(f"[worker] fim · {len(notas) - falhas} ok · {falhas} com erro")
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
