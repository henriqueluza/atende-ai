import uuid

import pytest
from core_api.dominio import Documento, Trecho, Visibilidade
from core_api.embeddings import EmbedderFalso
from core_api.repositorio_postgres import RepositorioPostgres

DIMENSAO = 16  # a mesma do conftest.py
embedder = EmbedderFalso(DIMENSAO)


def _salvar(repositorio, nome, visibilidade, *textos):
    trechos = [Trecho(t, e) for t, e in zip(textos, embedder.gerar(list(textos)), strict=True)]
    repositorio.salvar(Documento(str(uuid.uuid4()), nome, visibilidade), trechos)


def _buscar(repositorio, pergunta, visibilidade, k=10):
    [vetor] = embedder.gerar([pergunta])
    return repositorio.buscar(vetor, k, visibilidade)


def test_busca_ordena_do_mais_parecido_para_o_menos(repositorio):
    _salvar(repositorio, "faq.md", Visibilidade.PUBLICO, "preço do corte", "horário de abertura")

    resultados = _buscar(repositorio, "horário de abertura", Visibilidade.PUBLICO)

    assert [r.trecho for r in resultados] == ["horário de abertura", "preço do corte"]
    assert resultados[0].documento == "faq.md"
    assert resultados[0].score == pytest.approx(1.0)
    assert all(0 <= r.score <= 1 for r in resultados)


def test_busca_publica_nunca_devolve_trecho_de_documento_interno(repositorio):
    _salvar(repositorio, "faq.md", Visibilidade.PUBLICO, "horário de abertura")
    _salvar(repositorio, "margens.md", Visibilidade.INTERNO, "horário de abertura margem secreta")

    publicos = _buscar(repositorio, "horário de abertura margem secreta", Visibilidade.PUBLICO)
    internos = _buscar(repositorio, "horário de abertura margem secreta", Visibilidade.INTERNO)

    assert [r.documento for r in publicos] == ["faq.md"]
    assert [r.documento for r in internos] == ["margens.md"]


def test_salvar_o_mesmo_nome_substitui_inclusive_a_visibilidade(repositorio):
    _salvar(repositorio, "tabela.md", Visibilidade.PUBLICO, "preço antigo", "outro trecho")
    _salvar(repositorio, "tabela.md", Visibilidade.INTERNO, "preço novo")

    assert _buscar(repositorio, "preço", Visibilidade.PUBLICO) == []
    assert [r.trecho for r in _buscar(repositorio, "preço", Visibilidade.INTERNO)] == ["preço novo"]


def test_busca_respeita_k_e_aceita_pergunta_sem_palavras(repositorio):
    _salvar(repositorio, "faq.md", Visibilidade.PUBLICO, "um trecho", "dois trechos", "três")

    assert len(_buscar(repositorio, "trecho", Visibilidade.PUBLICO, k=2)) == 2
    assert all(r.score == 0 for r in _buscar(repositorio, "?!", Visibilidade.PUBLICO))


def test_postgres_recusa_iniciar_com_dimensao_diferente_da_do_banco(url_postgres_limpo):
    RepositorioPostgres(url_postgres_limpo, DIMENSAO).preparar()

    with pytest.raises(RuntimeError, match="dimensões"):
        RepositorioPostgres(url_postgres_limpo, DIMENSAO + 1).preparar()
