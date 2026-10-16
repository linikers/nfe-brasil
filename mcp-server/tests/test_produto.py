"""Testes da resolucao de codigos fiscais a partir da descricao do produto.

O teste central e `test_busca_textual_nao_classifica_produto`: ele documenta a
armadilha que motivou o desenho do modulo — casar texto livre com a nomenclatura
oficial leva "coca-cola" para `coca` (planta, NCM 1211) e `cola` (adesivo).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from nfe_brasil.nfe.emissao.produto import (
    Catalogo,
    ProdutoError,
    buscar_ncm,
    normalizar,
    resolver_produto,
)


@pytest.fixture
def catalogo(tmp_path: Path) -> Catalogo:
    cat = Catalogo(tmp_path / "catalogo.db")
    # semeado com o que ja foi autorizado pela SEFAZ (cStat 100)
    cat.registrar(
        "REFRIGERANTE COCA-COLA 350ML",
        "22021000",
        cfop="5405",
        csosn="500",
        ean="7894900011517",
    )
    cat.registrar("COCA-COLA 1 LITRO", "22021000", cfop="5405", csosn="500")
    return cat


def test_normalizar_tira_acento_pontuacao_e_caixa() -> None:
    assert normalizar("Refrigerante  COCA-COLA® 350ml") == "refrigerante coca cola 350ml"
    assert normalizar("ÁGUA  MINERAL") == "agua mineral"


def test_resolve_por_descricao_exata(catalogo: Catalogo) -> None:
    codigos = resolver_produto("REFRIGERANTE COCA-COLA 350ML", catalogo=catalogo)

    assert codigos.ncm == "22021000"
    assert codigos.cfop == "5405"
    assert codigos.csosn == "500"
    assert codigos.origem == "catalogo"
    assert codigos.precisa_conferir is False


def test_resolve_por_ean_tem_prioridade(catalogo: Catalogo) -> None:
    # descricao diferente, mas o EAN aponta para o produto certo
    codigos = resolver_produto("REFRI LATA", ean="7894900011517", catalogo=catalogo)

    assert codigos.ncm == "22021000"
    assert codigos.origem == "ean"
    assert codigos.descricao == "REFRIGERANTE COCA-COLA 350ML"


def test_resolve_descricao_parecida(catalogo: Catalogo) -> None:
    codigos = resolver_produto("Coca Cola 350 ml", catalogo=catalogo)

    assert codigos.ncm == "22021000"
    assert codigos.origem == "catalogo_similar"


def test_produto_desconhecido_nao_recebe_codigo_chutado(catalogo: Catalogo) -> None:
    """Sem correspondencia no catalogo, o modulo nao inventa NCM."""
    codigos = resolver_produto("COXINHA DE FRANGO", catalogo=catalogo)

    assert codigos.ncm is None
    assert codigos.csosn is None
    assert codigos.origem == "sem_match"
    assert codigos.precisa_conferir is True


def test_to_item_recusa_emitir_sem_codigo_confirmado(catalogo: Catalogo) -> None:
    codigos = resolver_produto("COXINHA DE FRANGO", catalogo=catalogo)

    with pytest.raises(ProdutoError, match="sem NCM"):
        codigos.to_item(quantidade="1", valor_unitario="8.00")


def test_to_item_monta_item_para_a_nota(catalogo: Catalogo) -> None:
    codigos = resolver_produto("COCA-COLA 1 LITRO", catalogo=catalogo)
    item = codigos.to_item(quantidade="1", valor_unitario="12.00")

    assert item.ncm == "22021000"
    assert item.cfop == "5405"
    assert item.csosn == "500"
    assert item.quantidade == Decimal("1")
    assert item.valor_unitario == Decimal("12.00")
    assert item.valor_total == Decimal("12.00")


def test_busca_textual_nao_classifica_produto() -> None:
    """Armadilha documentada: nome comercial nao casa com a descricao fiscal.

    Se este teste comecar a falhar porque "coca cola" passou a devolver algo, e
    sinal de que a busca ficou permissiva demais — e nota fiscal errada e multa.
    """
    assert buscar_ncm("REFRIGERANTE COCA-COLA 350ML") == []


def test_busca_textual_serve_para_conferencia_humana() -> None:
    """Com termos que existem na nomenclatura, a busca devolve opcoes para escolher."""
    resultados = buscar_ncm("agua mineral")

    assert resultados, "esperava resultados para um termo que existe na tabela fiscal"
    assert all("agua" in normalizar(c.caminho) for c in resultados)
