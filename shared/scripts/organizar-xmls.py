#!/usr/bin/env python3
"""
Organiza XMLs de NF-e em pastas por data/emitente.

Extrai a data de emissão e CNPJ do emitente de cada XML
e organiza em pastas: YYYY-MM/CNPJ/
"""

import os
import shutil
import sys
from datetime import datetime
from lxml import etree


def organizar_xmls(pasta_origem: str, pasta_destino: str) -> int:
    """Organiza XMLs de NF-e em pastas por mês/ano e CNPJ emitente."""
    ns = {"ns": "http://www.portalfiscal.inf.br/nfe"}
    contador = 0

    if not os.path.exists(pasta_origem):
        print(f"Pasta de origem não encontrada: {pasta_origem}")
        return 0

    os.makedirs(pasta_destino, exist_ok=True)

    for fname in os.listdir(pasta_origem):
        if not fname.lower().endswith(".xml"):
            continue

        path = os.path.join(pasta_origem, fname)
        try:
            tree = etree.parse(path)
            root = tree.getroot()
            infNFe = root.find(".//ns:infNFe", ns)

            if infNFe is None:
                # Tentar sem namespace
                infNFe = root.find(".//infNFe")

            if infNFe is None:
                print(f"AVISO: {fname} não parece ser NF-e válida")
                continue

            # Extrair data de emissão
            ide = infNFe.find("ns:ide", ns) or infNFe.find("ide")
            dh_emi = None
            if ide is not None:
                dh_emi_el = ide.find("ns:dhEmi", ns) or ide.find("dhEmi")
                if dh_emi_el is not None and dh_emi_el.text:
                    dh_emi = dh_emi_el.text

            # Extrair CNPJ emitente
            emit = infNFe.find("ns:emit", ns) or infNFe.find("emit")
            cnpj = "sem_cnpj"
            if emit is not None:
                cnpj_el = emit.find("ns:CNPJ", ns) or emit.find("CNPJ")
                if cnpj_el is not None and cnpj_el.text:
                    cnpj = cnpj_el.text

            # Montar caminho de destino
            if dh_emi:
                try:
                    dt = datetime.fromisoformat(dh_emi)
                    mes_ano = dt.strftime("%Y-%m")
                except ValueError:
                    mes_ano = "sem_data"
            else:
                mes_ano = "sem_data"

            destino = os.path.join(pasta_destino, mes_ano, cnpj)
            os.makedirs(destino, exist_ok=True)

            # Copiar arquivo
            shutil.copy2(path, os.path.join(destino, fname))
            contador += 1
            print(f"OK: {fname} -> {mes_ano}/{cnpj}/")

        except Exception as e:
            print(f"ERRO ao processar {fname}: {e}")

    return contador


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python organizar-xmls.py <pasta_origem> <pasta_destino>")
        print("Exemplo: python organizar-xmls.py ./xmls_brutos ./xmls_organizados")
        sys.exit(1)

    pasta_origem = sys.argv[1]
    pasta_destino = sys.argv[2]

    total = organizar_xmls(pasta_origem, pasta_destino)
    print(f"\nTotal: {total} XMLs organizados")
