#!/usr/bin/env python3
"""Emite uma NF-e (55) ou NFC-e (65) a partir de um payload JSON.

Exemplos:

    # Conferir o XML sem transmitir (nao gera documento fiscal)
    python examples/emitir_nota.py --pfx certificado.pfx --senha 123456 \
        --payload payload-exemplo.json

    # Transmitir em HOMOLOGACAO (sem valor fiscal)
    python examples/emitir_nota.py --pfx certificado.pfx --senha 123456 \
        --payload payload-exemplo.json --transmitir

    # Transmitir em PRODUCAO (nota real) - exige --producao explicito
    python examples/emitir_nota.py --pfx certificado.pfx --senha 123456 \
        --payload payload-exemplo.json --transmitir --producao

O payload segue o modelo `nfe_brasil.nfe.emissao.schemas.DadosNota`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nfe_brasil.nfe.emissao import (
    CertificadoA1,
    CertificadoError,
    ChaveInvalidaError,
    DadosNota,
    SefazError,
    emitir,
)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Emite NF-e (55) ou NFC-e (65).")
    parser.add_argument("--pfx", required=True, help="Arquivo .pfx/.p12 do certificado A1")
    parser.add_argument("--senha", required=True, help="Senha do certificado A1")
    parser.add_argument("--payload", required=True, help="JSON com os dados da nota")
    parser.add_argument("--transmitir", action="store_true", help="Envia para a SEFAZ")
    parser.add_argument(
        "--producao",
        action="store_true",
        help="Confirma emissao em PRODUCAO (nota com valor fiscal real)",
    )
    parser.add_argument("--uf", default="PR", help="UF do emitente (padrao PR)")
    parser.add_argument("--salvar-xml", help="Diretorio para gravar o XML assinado")
    return parser.parse_args()


def main() -> int:
    args = _args()

    dados = DadosNota.model_validate(json.loads(Path(args.payload).read_text(encoding="utf-8")))

    if args.producao:
        dados = dados.model_copy(update={"ambiente": "1"})
    if dados.ambiente == "1" and not args.producao:
        print("BLOQUEADO: ambiente=1 (producao) exige a flag --producao", file=sys.stderr)
        return 2

    try:
        certificado = CertificadoA1(args.pfx, args.senha)
    except CertificadoError as exc:
        print(f"CERTIFICADO: {exc}", file=sys.stderr)
        return 3

    info = certificado.info()
    print(f"Certificado : {info.titular}")
    print(f"CNPJ        : {info.cnpj or info.cpf}")
    print(f"Validade    : {info.valido_ate:%d/%m/%Y} ({info.dias_para_expirar} dias)")
    if info.expirado:
        print("CERTIFICADO EXPIRADO", file=sys.stderr)
        return 3

    ambiente = "PRODUCAO" if dados.ambiente == "1" else "HOMOLOGACAO (sem valor fiscal)"
    print(f"Ambiente    : {ambiente}")
    print(f"Modelo      : {'NFC-e (65)' if dados.modelo == '65' else 'NF-e (55)'}")
    print(f"Valor total : R$ {dados.valor_total}")
    print(f"Destinatario: {dados.destinatario.identificacao() if dados.destinatario else 'nao identificado'}")
    print(f"Transmitir  : {'SIM' if args.transmitir else 'nao (apenas monta e assina)'}")

    try:
        resultado = emitir(dados, certificado, enviar_de_verdade=args.transmitir, uf=args.uf)
    except ChaveInvalidaError as exc:
        print(f"CHAVE: {exc}", file=sys.stderr)
        return 4
    except SefazError as exc:
        print(f"SEFAZ: {exc}", file=sys.stderr)
        return 5

    print()
    print(resultado.resumo())
    if resultado.xml_retorno:
        print("--- retorno da SEFAZ ---")
        print(resultado.xml_retorno[:2000])

    destino = Path(args.salvar_xml) if args.salvar_xml else Path(".")
    destino.mkdir(parents=True, exist_ok=True)
    if resultado.xml_nfe:
        arquivo = destino / f"NFe-{resultado.chave}.xml"
        arquivo.write_text(resultado.xml_nfe, encoding="utf-8")
        print(f"XML salvo   : {arquivo}")

    return 0 if (resultado.autorizada or not args.transmitir) else 1


if __name__ == "__main__":
    raise SystemExit(main())
