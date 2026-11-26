import uuid

import pytest
from core_api.dominio import (
    AcervoIndisponivel,
    Consulta,
    Documento,
    Situacao,
    Trecho,
    Visibilidade,
)
from core_api.embeddings import EmbedderFalso
from core_api.repositorio_postgres import RepositorioPostgres

DIMENSAO = 16  # a mesma do conftest.py
embedder = EmbedderFalso(DIMENSAO)


def _salvar(repositorio, nome, visibilidade, *textos):
    trechos = [Trecho(t, e) for t, e in zip(textos, embedder.gerar(list(textos)), strict=True)]
    repositorio.salvar(Documento(str(uuid.uuid4()), nome, visibilidade), trechos)


def _buscar(repositorio, pergunta, visibilidade, k=10):
    [vetor] = embedder.gerar([pergunta])
    return repositorio.buscar(Consulta(pergunta, vetor, k, visibilidade))


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


def test_listar_conta_os_trechos_e_excluir_apaga_tudo(repositorio):
    _salvar(repositorio, "faq.md", Visibilidade.PUBLICO, "horário de abertura", "preço do corte")
    _salvar(repositorio, "margens.md", Visibilidade.INTERNO, "margem secreta")

    lista = {d.nome: d for d in repositorio.listar()}

    assert {nome: (d.visibilidade, d.trechos) for nome, d in lista.items()} == {
        "faq.md": (Visibilidade.PUBLICO, 2),
        "margens.md": (Visibilidade.INTERNO, 1),
    }
    assert repositorio.excluir(lista["faq.md"].id) is True
    assert repositorio.excluir(lista["faq.md"].id) is False
    assert [d.nome for d in repositorio.listar()] == ["margens.md"]
    assert _buscar(repositorio, "horário de abertura", Visibilidade.PUBLICO) == []


def test_fila_entrega_o_mais_antigo_guarda_os_trechos_e_registra_a_falha(repositorio):
    primeiro, segundo = (Documento(str(uuid.uuid4()), nome, Visibilidade.PUBLICO) for nome in "ab")
    repositorio.enfileirar(primeiro, b"conteudo a")
    repositorio.enfileirar(segundo, b"conteudo b")
    assert {d.nome: (d.situacao, d.trechos) for d in repositorio.listar()} == {
        "a": (Situacao.NA_FILA, 0),
        "b": (Situacao.NA_FILA, 0),
    }

    arquivo = repositorio.proximo_da_fila()
    assert (arquivo.documento.nome, arquivo.conteudo) == ("a", b"conteudo a")
    repositorio.registrar_andamento(primeiro.id, Situacao.EXTRAINDO, "Lendo a página 1 de 2")
    assert repositorio.obter(primeiro.id).andamento == "Lendo a página 1 de 2"
    [vetor] = embedder.gerar(["texto da página dois"])
    repositorio.concluir(primeiro.id, [Trecho("texto da página dois", vetor, 2)], True, 2)
    repositorio.falhar(repositorio.proximo_da_fila().documento.id, "O PDF está com senha.")

    assert repositorio.proximo_da_fila() is None
    pronto, falho = repositorio.obter(primeiro.id), repositorio.obter(segundo.id)
    assert (pronto.situacao, pronto.trechos, pronto.ocr, pronto.paginas) == (
        Situacao.INDEXADO,
        1,
        True,
        2,
    )
    assert pronto.andamento is None
    assert [(t.posicao, t.texto, t.pagina) for t in repositorio.trechos_de(primeiro.id)] == [
        (0, "texto da página dois", 2)
    ]
    assert (falho.situacao, falho.erro) == (Situacao.FALHOU, "O PDF está com senha.")
    assert _buscar(repositorio, "página dois", Visibilidade.PUBLICO)[0].documento == "a"


def test_documento_interrompido_volta_para_a_fila_e_excluido_nao_ressuscita(repositorio):
    documento = Documento(str(uuid.uuid4()), "escala.pdf", Visibilidade.INTERNO)
    repositorio.enfileirar(documento, b"pdf")
    repositorio.proximo_da_fila()  # começou a processar e o serviço caiu

    assert repositorio.retomar_interrompidos() == 1
    assert repositorio.proximo_da_fila().documento.id == documento.id

    repositorio.excluir(documento.id)
    [vetor] = embedder.gerar(["texto"])
    repositorio.concluir(documento.id, [Trecho("texto", vetor)], False, 1)  # chegou tarde
    assert repositorio.listar() == []
    assert _buscar(repositorio, "texto", Visibilidade.INTERNO) == []


def test_trocar_a_visibilidade_muda_quem_encontra_o_documento(repositorio):
    _salvar(repositorio, "precos.md", Visibilidade.PUBLICO, "preço do corte")
    [documento] = repositorio.listar()

    assert repositorio.alterar_visibilidade(documento.id, Visibilidade.INTERNO) is True
    assert repositorio.alterar_visibilidade(str(uuid.uuid4()), Visibilidade.INTERNO) is False

    assert _buscar(repositorio, "preço do corte", Visibilidade.PUBLICO) == []
    assert [r.documento for r in _buscar(repositorio, "preço", Visibilidade.INTERNO)] == [
        "precos.md"
    ]


def test_postgres_atualiza_um_banco_criado_na_etapa_1_sem_perder_os_dados(url_postgres_limpo):
    import psycopg

    with psycopg.connect(url_postgres_limpo) as conexao:
        conexao.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conexao.execute(
            "CREATE TABLE documentos (id uuid PRIMARY KEY, nome text NOT NULL UNIQUE, "
            "visibilidade text NOT NULL, criado_em timestamptz NOT NULL DEFAULT now())"
        )
        conexao.execute(
            "CREATE TABLE trechos (id bigserial PRIMARY KEY, documento_id uuid NOT NULL "
            "REFERENCES documentos (id) ON DELETE CASCADE, posicao integer NOT NULL, "
            f"texto text NOT NULL, embedding vector({DIMENSAO}) NOT NULL)"
        )
        id = str(uuid.uuid4())
        conexao.execute(
            "INSERT INTO documentos (id, nome, visibilidade) VALUES (%s, 'faq.md', 'publico')",
            (id,),
        )
        vetor = "[" + ",".join(map(str, embedder.gerar(["horário antigo"])[0])) + "]"
        conexao.execute(
            "INSERT INTO trechos (documento_id, posicao, texto, embedding) "
            "VALUES (%s, 0, 'horário antigo', %s::vector)",
            (id, vetor),
        )

    repositorio = RepositorioPostgres(url_postgres_limpo, DIMENSAO)
    repositorio.preparar()

    [documento] = repositorio.listar()
    assert (documento.nome, documento.situacao, documento.trechos) == (
        "faq.md",
        Situacao.INDEXADO,
        1,
    )
    assert [r.trecho for r in _buscar(repositorio, "horário antigo", Visibilidade.PUBLICO)] == [
        "horário antigo"
    ]


def test_postgres_recusa_iniciar_com_dimensao_diferente_da_do_banco(url_postgres_limpo):
    RepositorioPostgres(url_postgres_limpo, DIMENSAO).preparar()

    with pytest.raises(RuntimeError, match="dimensões"):
        RepositorioPostgres(url_postgres_limpo, DIMENSAO + 1).preparar()


def test_falha_do_banco_no_meio_da_operacao_vira_acervo_indisponivel(url_postgres_limpo):
    repositorio = RepositorioPostgres(url_postgres_limpo, DIMENSAO)  # sem preparar: não há tabela

    with pytest.raises(AcervoIndisponivel):
        _buscar(repositorio, "horário", Visibilidade.PUBLICO)
