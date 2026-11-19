import httpx
import pytest
from core_api.acervo import Acervo
from core_api.config import montar_acervo
from core_api.dominio import AcervoIndisponivel
from core_api.embeddings import EmbedderOpenAI
from core_api.main import criar_app
from core_api.repositorio_memoria import RepositorioMemoria
from fastapi.testclient import TestClient


def _embedder(responder):
    cliente = httpx.Client(transport=httpx.MockTransport(responder))
    return EmbedderOpenAI("https://exemplo.test/v1/", "modelo-x", "chave-de-teste", 2, cliente)


def test_embedder_real_chama_o_endpoint_e_devolve_os_vetores_na_ordem():
    def responder(requisicao: httpx.Request) -> httpx.Response:
        assert requisicao.url == "https://exemplo.test/v1/embeddings"
        assert requisicao.headers["authorization"] == "Bearer chave-de-teste"
        dados = [{"index": 1, "embedding": [0, 1]}, {"index": 0, "embedding": [1, 0]}]
        return httpx.Response(200, json={"data": dados})

    assert _embedder(responder).gerar(["a", "b"]) == [[1.0, 0.0], [0.0, 1.0]]


@pytest.mark.parametrize(
    "resposta",
    [
        httpx.Response(401, json={"error": "chave inválida"}),
        httpx.Response(200, json={"inesperado": True}),
        httpx.Response(200, json={"data": [{"index": 0, "embedding": [1, 2, 3]}]}),
    ],
)
def test_falha_do_servico_de_embeddings_vira_503_sem_vazar_detalhe(resposta):
    acervo = Acervo(RepositorioMemoria(), _embedder(lambda _: resposta))
    api = TestClient(criar_app(acervo), base_url="http://localhost")

    busca = api.get("/busca", params={"pergunta": "oi"})

    assert busca.status_code == 503
    assert busca.json() == {"detail": "Serviço temporariamente indisponível."}
    with pytest.raises(AcervoIndisponivel):
        acervo.buscar("oi", 1, "publico")


def test_sem_configuracao_usa_embedder_falso_e_memoria():
    acervo = montar_acervo({})

    acervo.ingerir("faq.md", "horário de abertura", "publico")
    assert acervo.buscar("horário", 1, "publico")[0].documento == "faq.md"


@pytest.mark.parametrize(
    "ambiente",
    [
        {"EMBEDDINGS_PROVIDER": "outro"},
        {"EMBEDDINGS_PROVIDER": "openai"},  # falta modelo e chave
        {"EMBEDDINGS_PROVIDER": "openai", "EMBEDDINGS_MODEL": "m"},  # falta chave
    ],
)
def test_configuracao_invalida_impede_o_inicio(ambiente):
    with pytest.raises(RuntimeError):
        montar_acervo(ambiente)
