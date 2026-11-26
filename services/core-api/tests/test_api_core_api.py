import pytest
from core_api.config import montar_acervo
from core_api.main import criar_app
from fastapi.testclient import TestClient

FAQ = "## Horário de funcionamento\n\nAbrimos de terça a sábado, das 9h às 19h."
SIGILOSO = "## Horário de funcionamento da diretoria\n\nMargem de lucro secreta: 62%."


@pytest.fixture
def api():
    return TestClient(
        criar_app(montar_acervo({})), base_url="http://localhost"
    )  # em memória, embedder falso


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


def test_requisicao_com_host_desconhecido_e_recusada(api):
    resposta = api.get("/busca", params={"pergunta": "oi"}, headers={"host": "site-malicioso.test"})

    assert resposta.status_code == 400


def test_lista_traz_publicos_e_internos_com_a_contagem_de_trechos(api):
    _ingerir(api, "faq.md", FAQ + "\n\n## Endereço\n\nRua das Acácias, 120.", "publico")
    _ingerir(api, "margens.md", SIGILOSO, "interno")

    lista = api.get("/documentos")

    assert lista.status_code == 200
    documentos = {d["nome"]: d for d in lista.json()["documentos"]}
    assert documentos["faq.md"]["visibilidade"] == "publico"
    assert documentos["faq.md"]["trechos"] == 2
    assert documentos["margens.md"]["visibilidade"] == "interno"
    assert all(d["id"] and d["criado_em"] for d in documentos.values())


def test_excluir_tira_o_documento_da_lista_e_da_busca(api):
    id = _ingerir(api, "faq.md", FAQ, "publico").json()["id"]

    assert api.delete(f"/documentos/{id}").status_code == 204

    assert api.get("/documentos").json()["documentos"] == []
    assert api.get("/busca", params={"pergunta": "horário"}).json()["resultados"] == []


def test_excluir_documento_inexistente_ou_com_id_invalido(api):
    assert api.delete("/documentos/00000000-0000-4000-8000-000000000000").status_code == 404
    assert api.delete("/documentos/nao-e-um-id").status_code == 422
