"""Resolucao de codigos fiscais a partir da descricao do produto.

Ideia: o operador descreve o item ("REFRIGERANTE COCA-COLA 350ML") e o sistema
devolve NCM, CFOP, CSOSN e unidade.

Como isso funciona na pratica (e por que):

1. **Catalogo (melhor caminho).** O produto ja emitido antes e resolvido por
   codigo de barras (EAN) ou pela descricao exata. Uma vez confirmado, toda
   emissao seguinte e automatica. Este modulo mantem esse catalogo.
2. **Sugestao a partir da tabela oficial.** Para produto novo, o texto e
   comparado com a nomenclatura oficial do Siscomex (10.5 mil NCMs, carregados
   por `scripts/atualizar_ncm.py`). Serve como *sugestao*, nunca como verdade:
   a descricao fiscal ("Aguas ... adicionadas de acucar ou aromatizadas") quase
   nunca coincide com o nome comercial ("Coca-Cola"), entao o resultado precisa
   de conferencia humana.

Ou seja: descricao livre sozinha NAO determina o NCM. O caminho confiavel e o
catalogo (EAN > descricao confirmada) e a sugestao entra apenas como apoio.
"""

from __future__ import annotations

import os
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from .schemas import Item

BANCO_TABELAS = (
    Path(__file__).resolve().parent.parent.parent / "tabelas" / "data" / "tabelas_fiscais.db"
)

CATALOGO_PADRAO = Path(
    os.environ.get("NFE_CATALOGO_DB", str(Path.home() / ".nfe-brasil" / "catalogo.db"))
)

# CFOP de venda dentro do estado (NFC-e) e codigos do Simples Nacional.
CFOP_VENDA_INTERNA = "5405"  # venda de mercadoria sujeita a ST, ja tributada
CFOP_VENDA_INTERNA_SEM_ST = "5102"  # venda de mercadoria adquirida de terceiros
CSOSN_ST = "500"  # ICMS cobrado anteriormente por substituicao tributaria
CSOSN_SEM_CREDITO = "102"  # tributada pelo Simples sem permissao de credito

_PALAVRAS_IGNORADAS = {
    "de", "da", "do", "das", "dos", "com", "sem", "para", "por", "em", "no",
    "na", "nos", "nas", "e", "ou", "ao", "aos", "as", "os", "um", "uma", "ml",
    "lt", "lts", "kg", "un", "und", "cx", "pct", "ref", "cod", "tipo",
}

DDL_CATALOGO = """
CREATE TABLE IF NOT EXISTS produto_catalogo (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao_norm      TEXT NOT NULL,
    descricao           TEXT NOT NULL,
    ean                 TEXT,
    ncm                 TEXT NOT NULL,
    cfop                TEXT NOT NULL,
    csosn               TEXT NOT NULL,
    unidade             TEXT NOT NULL DEFAULT 'UN',
    confirmado          INTEGER NOT NULL DEFAULT 0,
    atualizado_em       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (descricao_norm)
);
CREATE INDEX IF NOT EXISTS idx_catalogo_ean ON produto_catalogo (ean);
"""


class ProdutoError(ValueError):
    """Nao foi possivel resolver os codigos do produto."""


@dataclass
class Candidato:
    ncm: str
    descricao: str
    caminho: str
    pontos: float


@dataclass
class CodigosProduto:
    """Codigos fiscais resolvidos para um produto."""

    descricao: str
    ncm: str | None = None
    cfop: str | None = None
    csosn: str | None = None
    unidade: str = "UN"
    origem: str = "sem_match"  # ean | catalogo | ncm_sugerido | sem_match
    precisa_conferir: bool = True
    candidatos: list[Candidato] = field(default_factory=list)

    def to_item(self, quantidade: str, valor_unitario: str, **extras: Any) -> Item:
        """Monta o Item da nota com os codigos resolvidos."""
        if not self.ncm or not self.csosn:
            raise ProdutoError(
                f"Produto '{self.descricao}' sem NCM/CSOSN confirmado — "
                "confirme os codigos antes de emitir."
            )
        return Item(
            codigo=str(extras.pop("codigo", self.descricao[:20].upper())),
            descricao=self.descricao,
            ncm=self.ncm,
            cfop=self.cfop or CFOP_VENDA_INTERNA,
            unidade=self.unidade,
            quantidade=Decimal(quantidade),
            valor_unitario=Decimal(valor_unitario),
            csosn=self.csosn,
            **extras,
        )


# --------------------------------------------------------------------------- #
# Normalizacao e busca textual
# --------------------------------------------------------------------------- #


def normalizar(texto: str) -> str:
    """Minusculas, sem acento e sem pontuacao — para comparação de descricoes."""
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    apenas_ascii = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", apenas_ascii)).strip()


def _tokens(texto: str) -> list[str]:
    return [t for t in normalizar(texto).split() if len(t) >= 4 and t not in _PALAVRAS_IGNORADAS]


@lru_cache(maxsize=1)
def _nomenclatura() -> list[tuple[str, str, str]]:
    """Carrega (codigo, descricao, caminho) da tabela oficial do Siscomex."""
    if not BANCO_TABELAS.exists():
        raise ProdutoError(
            f"Tabela de NCM nao encontrada em {BANCO_TABELAS}. "
            "Rode: python scripts/atualizar_ncm.py"
        )
    conexao = sqlite3.connect(BANCO_TABELAS)
    try:
        colunas = {linha[1] for linha in conexao.execute("PRAGMA table_info(ncm)")}
        campo = "caminho" if "caminho" in colunas else "descricao"
        return [
            (codigo, descricao, caminho or descricao)
            for codigo, descricao, caminho in conexao.execute(
                f"SELECT codigo, descricao, {campo} FROM ncm"
            )
        ]
    finally:
        conexao.close()


def _radical(token: str) -> str:
    """Reduz plurais irregulares do portugues para comparar termos.

    -al/-ais, -el/-eis, -il/-is e o plural simples em -s. Sem isso "mineral"
    nunca casa com "minerais", que e como a nomenclatura fiscal escreve.
    """
    for plural, singular in (("ais", "al"), ("eis", "el"), ("is", "il"), ("es", "e")):
        if token.endswith(plural) and len(token) > len(plural) + 2:
            return token[: -len(plural)] + singular
    return token[:-1] if token.endswith("s") and len(token) > 4 else token


def _casa_termo(termo: str, tokens_caminho: set[str]) -> bool:
    """Casa o termo com a nomenclatura tolerando plural.

    "agua" casa com "aguas" e "mineral" com "minerais"; "agua" NAO casa com
    "aguardente" (a diferenca de tamanho e limitada a 3 caracteres).
    """
    alvo = _radical(termo)
    return any(
        _radical(token) == alvo
        or (_radical(token).startswith(alvo) and len(_radical(token)) - len(alvo) <= 3)
        for token in tokens_caminho
    )


def buscar_ncm(texto: str, limite: int = 10) -> list[Candidato]:
    """Busca NCMs na nomenclatura oficial para conferencia HUMANA.

    Esta funcao NAO classifica produto — ela e uma busca para o operador olhar
    a tabela e escolher. Exige que TODOS os termos relevantes do texto aparecam
    no NCM, senao a busca retorna lixo: "coca-cola" bate em `coca` (a planta,
    NCM 1211) e em `cola` (adesivo).

    Por isso a classificacao automatica vem do catalogo de produtos
    (`Catalogo`), alimentado pelo EAN ou pela descricao ja confirmada — nunca
    desta busca.
    """
    termos = set(_tokens(texto))
    if not termos:
        return []

    encontrados: list[Candidato] = []
    for codigo, descricao_ncm, caminho in _nomenclatura():
        tokens_caminho = set(_tokens(caminho))
        if not all(_casa_termo(termo, tokens_caminho) for termo in termos):
            continue
        encontrados.append(
            Candidato(
                ncm=codigo,
                descricao=descricao_ncm,
                caminho=caminho,
                pontos=float(len(termos)),
            )
        )

    encontrados.sort(key=lambda c: c.ncm)
    return encontrados[:limite]


def _similaridade(texto_a: str, texto_b: str) -> float:
    """Similaridade de Jaccard entre os termos de duas descricoes (0 a 1)."""
    tokens_a, tokens_b = set(_tokens(texto_a)), set(_tokens(texto_b))
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


# --------------------------------------------------------------------------- #
# Catalogo de produtos
# --------------------------------------------------------------------------- #


class Catalogo:
    """Catalogo de produtos ja resolvidos (aprendido a cada confirmacao)."""

    def __init__(self, caminho: Path | None = None) -> None:
        self.caminho = Path(caminho or CATALOGO_PADRAO)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        conexao = sqlite3.connect(self.caminho)
        try:
            conexao.executescript(DDL_CATALOGO)
            conexao.commit()
        finally:
            conexao.close()

    def _conectar(self) -> sqlite3.Connection:
        conexao = sqlite3.connect(self.caminho)
        conexao.row_factory = sqlite3.Row
        return conexao

    def registrar(
        self,
        descricao: str,
        ncm: str,
        *,
        ean: str | None = None,
        cfop: str = CFOP_VENDA_INTERNA,
        csosn: str = CSOSN_ST,
        unidade: str = "UN",
        confirmado: bool = True,
    ) -> None:
        """Grava (ou atualiza) um produto no catalogo."""
        conexao = self._conectar()
        try:
            conexao.execute(
                "INSERT INTO produto_catalogo "
                "(descricao_norm, descricao, ean, ncm, cfop, csosn, unidade, confirmado) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(descricao_norm) DO UPDATE SET "
                "descricao = excluded.descricao, ean = excluded.ean, ncm = excluded.ncm, "
                "cfop = excluded.cfop, csosn = excluded.csosn, unidade = excluded.unidade, "
                "confirmado = excluded.confirmado, atualizado_em = datetime('now')",
                (
                    normalizar(descricao),
                    descricao,
                    ean,
                    ncm,
                    cfop,
                    csosn,
                    unidade,
                    int(confirmado),
                ),
            )
            conexao.commit()
        finally:
            conexao.close()

    def buscar(self, descricao: str | None = None, ean: str | None = None) -> sqlite3.Row | None:
        conexao = self._conectar()
        try:
            if ean:
                linha = conexao.execute(
                    "SELECT * FROM produto_catalogo WHERE ean = ?", (ean,)
                ).fetchone()
                if linha:
                    return cast("sqlite3.Row | None", linha)
            if descricao:
                return cast(
                    "sqlite3.Row | None",
                    conexao.execute(
                        "SELECT * FROM produto_catalogo WHERE descricao_norm = ?",
                        (normalizar(descricao),),
                    ).fetchone(),
                )
            return None
        finally:
            conexao.close()

    def listar(self) -> list[sqlite3.Row]:
        conexao = self._conectar()
        try:
            return list(conexao.execute("SELECT * FROM produto_catalogo ORDER BY descricao"))
        finally:
            conexao.close()

    def buscar_similar(self, descricao: str, limiar: float = 0.6) -> sqlite3.Row | None:
        """Melhor correspondencia do catalogo por similaridade de termos.

        Seguro porque compara dentro do proprio catalogo (poucos itens, curados
        pelo operador), e nao contra as 10 mil descricoes da tabela fiscal.
        """
        melhor: sqlite3.Row | None = None
        melhor_pontos = 0.0
        conexao = self._conectar()
        try:
            for linha in conexao.execute("SELECT * FROM produto_catalogo"):
                pontos = _similaridade(descricao, str(linha["descricao"]))
                if pontos > melhor_pontos:
                    melhor, melhor_pontos = linha, pontos
        finally:
            conexao.close()
        return melhor if melhor_pontos >= limiar else None


# --------------------------------------------------------------------------- #
# Resolucao
# --------------------------------------------------------------------------- #


def resolver_produto(
    descricao: str,
    *,
    ean: str | None = None,
    catalogo: Catalogo | None = None,
    unidade: str = "UN",
) -> CodigosProduto:
    """Resolve os codigos fiscais de um produto pelo catalogo.

    Ordem: EAN -> descricao exata -> descricao parecida (similaridade >= 0.6).
    Produto fora do catalogo NAO recebe codigo chutado: volta `sem_match` com
    `precisa_conferir=True` para o operador confirmar uma vez (e o item entra no
    catalogo para as proximas emissoes).
    """
    cat = catalogo or Catalogo()

    linha = cat.buscar(descricao=descricao, ean=ean)
    origem = "ean" if (linha is not None and ean) else "catalogo"

    if linha is None:
        linha = cat.buscar_similar(descricao)
        origem = "catalogo_similar"

    if linha is not None:
        return CodigosProduto(
            descricao=str(linha["descricao"]),
            ncm=str(linha["ncm"]),
            cfop=str(linha["cfop"]),
            csosn=str(linha["csosn"]),
            unidade=str(linha["unidade"] or unidade),
            origem=origem,
            precisa_conferir=not bool(linha["confirmado"]),
        )

    return CodigosProduto(
        descricao=descricao,
        ncm=None,
        cfop=None,
        csosn=None,
        unidade=unidade,
        origem="sem_match",
        precisa_conferir=True,
        candidatos=buscar_ncm(descricao, limite=5),
    )
