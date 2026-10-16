#!/usr/bin/env python3
"""Atualiza a tabela NCM do banco bundled com a nomenclatura oficial do Siscomex.

Fonte (publica, sem autenticacao):
    https://portalunico.siscomex.gov.br/classif/api/publico/nomenclatura/download/json

O banco bundled do projeto vinha com um subconjunto de amostra (138 codigos);
a nomenclatura vigente tem ~10.500 NCMs de 8 digitos. Sem a tabela completa e
impossivel resolver o codigo a partir da descricao do produto.

Uso:
    python scripts/atualizar_ncm.py                 # baixa e atualiza
    python scripts/atualizar_ncm.py --arquivo x.json  # usa arquivo local
    python scripts/atualizar_ncm.py --dry-run       # so mostra o resumo
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import urllib.request
from pathlib import Path

URL_NOMENCLATURA = (
    "https://portalunico.siscomex.gov.br/classif/api/publico/nomenclatura/download/json"
    "?perfil=PUBLICO"
)

BANCO = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "nfe_brasil"
    / "tabelas"
    / "data"
    / "tabelas_fiscais.db"
)


def baixar(destino: Path) -> Path:
    print(f"baixando nomenclatura oficial -> {destino}")
    requisicao = urllib.request.Request(URL_NOMENCLATURA, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(requisicao, timeout=120) as resposta:
        conteudo = resposta.read()
    destino.write_bytes(conteudo)
    print(f"  {len(conteudo) / 1_048_576:.1f} MB")
    return destino


def carregar(caminho: Path) -> tuple[str, str, list[tuple[str, str, str]]]:
    """Le a nomenclatura e devolve (atualizacao, ato, registros).

    Cada registro e (codigo, descricao, caminho) — o `caminho` concatena a
    hierarquia (capitulo > posicao > subposicao > item), porque a descricao do
    NCM de 8 digitos isolada costuma ser apenas "Outras".
    """
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    atualizacao = dados.get("Data_Ultima_Atualizacao_NCM", "")
    ato = dados.get("Ato", "")

    # mapa de prefixo -> descricao, para montar o caminho de cada folha
    por_prefixo: dict[str, str] = {}
    for item in dados.get("Nomenclaturas", []):
        codigo = str(item.get("Codigo", "")).replace(".", "").strip()
        descricao = str(item.get("Descricao", "")).strip().lstrip("-").strip()
        if codigo and descricao and codigo.isdigit():
            por_prefixo[codigo] = descricao

    registros: list[tuple[str, str, str]] = []
    for codigo, descricao in por_prefixo.items():
        if len(codigo) != 8:
            continue
        niveis = [por_prefixo.get(codigo[:tamanho], "") for tamanho in (2, 4, 6)]
        caminho_niveis = [n for n in niveis if n]
        # evita repetir "Outras > Outras" no fim do caminho
        if caminho_niveis and caminho_niveis[-1] == descricao:
            caminho_niveis = caminho_niveis[:-1]
        registros.append((codigo, descricao, " > ".join([*caminho_niveis, descricao])))

    registros.sort()
    return atualizacao, ato, registros


def atualizar(banco: Path, registros: list[tuple[str, str, str]]) -> tuple[int, int]:
    conexao = sqlite3.connect(banco)
    try:
        colunas = {linha[1] for linha in conexao.execute("PRAGMA table_info(ncm)")}
        if "caminho" not in colunas:
            conexao.execute("ALTER TABLE ncm ADD COLUMN caminho TEXT")

        antes = conexao.execute("SELECT COUNT(*) FROM ncm").fetchone()[0]
        conexao.executemany(
            "INSERT INTO ncm (codigo, descricao, caminho) VALUES (?, ?, ?) "
            "ON CONFLICT(codigo) DO UPDATE SET "
            "descricao = excluded.descricao, caminho = excluded.caminho",
            registros,
        )
        conexao.commit()
        depois = conexao.execute("SELECT COUNT(*) FROM ncm").fetchone()[0]
    finally:
        conexao.close()
    return antes, depois


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arquivo", type=Path, help="JSON da nomenclatura ja baixado")
    parser.add_argument("--banco", type=Path, default=BANCO)
    parser.add_argument("--dry-run", action="store_true", help="nao grava no banco")
    args = parser.parse_args()

    if not args.banco.exists():
        print(f"banco nao encontrado: {args.banco}", file=sys.stderr)
        return 1

    arquivo = args.arquivo or baixar(Path("/tmp/ncm-siscomex.json"))
    atualizacao, ato, registros = carregar(arquivo)

    print(f"nomenclatura: {atualizacao} ({ato})")
    print(f"NCMs de 8 digitos no arquivo: {len(registros)}")

    if args.dry_run:
        return 0

    antes, depois = atualizar(args.banco, registros)
    print(f"banco {args.banco.name}: {antes} -> {depois} codigos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
