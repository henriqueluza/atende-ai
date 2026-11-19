import pytest
from core_api.config import montar_acervo
from core_api.main import criar_app
from fastapi.testclient import TestClient

FAQ = "## Horário de funcionamento\n\nAbrimos de terça a sábado, das 9h às 19h."
SIGILOSO = "## Horário de funcionamento da diretoria\n\nMargem de lucro secreta: 62%."


@pytest.fixture
def api():
    return TestClient(criar_app(montar_acervo({})))  # em memória, embedder falso


def _ingerir(api, nome, conteudo, visibilidade):
    return api.post(
        "/documentos", json={"nome": nome, "conteudo": conteudo, "visibilidade": visibilidade}
    )


def test_ingere_e_encontra_o_trecho_com_a_fonte(api):
    resposta = _ingerir(api, "faq.md", FAQ, "publico")
    assert resposta.status_code == 201
    assert resposta.json()["trechos"] == 1

    busca = api.get("/busca", params={"pergunta": "Qual o horário de funcionamento?"})

    assert busca.status_code == 200
    [resultado] = busca.json()["resultados"]
    assert resultado["documento"] == "faq.md"
    assert "terça a sábado" in resultado["trecho"]
    assert 0 < resultado["score"] <= 1


def test_documento_interno_nao_aparece_na_busca_publica_nem_na_busca_sem_parametro(api):
    _ingerir(api, "margens.md", SIGILOSO, "interno")
    pergunta = {"pergunta": "horário de funcionamento da diretoria margem de lucro"}

    sem_parametro = api.get("/busca", params=pergunta)
    publica = api.get("/busca", params=pergunta | {"visibilidade": "publico"})
    interna = api.get("/busca", params=pergunta | {"visibilidade": "interno"})

    assert sem_parametro.json()["resultados"] == []
    assert publica.json()["resultados"] == []
    assert [r["documento"] for r in interna.json()["resultados"]] == ["margens.md"]


def test_reenviar_documento_com_o_mesmo_nome_substitui_o_anterior(api):
    _ingerir(api, "faq.md", FAQ, "publico")
    _ingerir(api, "faq.md", "## Horário de funcionamento\n\nAgora abrimos aos domingos.", "publico")

    resultados = api.get("/busca", params={"pergunta": "horário", "k": 10}).json()["resultados"]

    assert [r["trecho"] for r in resultados] == [
        "## Horário de funcionamento\n\nAgora abrimos aos domingos."
    ]


@pytest.mark.parametrize(
    "corpo",
    [
        {"nome": "a.md", "conteudo": "texto"},  # sem visibilidade
        {"nome": "a.md", "conteudo": "texto", "visibilidade": "secreto"},
        {"nome": "", "conteudo": "texto", "visibilidade": "publico"},
        {"nome": "a.md", "conteudo": "   ", "visibilidade": "publico"},
    ],
)
def test_ingestao_recusa_entrada_invalida(api, corpo):
    assert api.post("/documentos", json=corpo).status_code == 422


@pytest.mark.parametrize(
    "parametros",
    [
        {"pergunta": ""},
        {"pergunta": "x" * 501},
        {"pergunta": "oi", "k": 0},
        {"pergunta": "oi", "k": 11},
        {"pergunta": "oi", "visibilidade": "todos"},
    ],
)
def test_busca_recusa_entrada_invalida(api, parametros):
    assert api.get("/busca", params=parametros).status_code == 422
