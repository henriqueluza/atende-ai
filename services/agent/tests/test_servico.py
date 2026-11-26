import pytest
from agent.atendente import ErroDeBusca
from agent.llm import SEM_RESPOSTA, ErroDoLLM, Fonte, LLMFalso
from agent.servico import criar_app
from fastapi.testclient import TestClient

FONTES = [
    Fonte("## Horário\n\nAbrimos das 9h às 19h.", "faq.md", 0.6),
    Fonte("## Preços\n\nCorte: R$ 80.", "faq.md", 0.05),
]


def _api(buscar, llm=None, monkeypatch=None):
    return TestClient(criar_app(buscar, llm or LLMFalso()), base_url="http://localhost")


async def _encontra(pergunta, k):
    return FONTES[:k]


async def _nada(pergunta, k):
    return []


def test_responde_com_o_texto_e_so_as_fontes_acima_do_corte():
    resposta = _api(_encontra).post("/perguntas", json={"pergunta": "Que horas abrem?"})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["texto"] == "Abrimos das 9h às 19h. [faq.md]"
    assert corpo["respondeu"] is True
    assert [f["score"] for f in corpo["fontes"]] == [0.6]


def test_sem_trecho_relevante_diz_que_nao_encontrou_sem_chamar_o_modelo():
    class ModeloQueNaoPodeSerChamado:
        def responder(self, pergunta, fontes):
            raise AssertionError("o modelo não deveria ser chamado")

    resposta = _api(_nada, ModeloQueNaoPodeSerChamado()).post("/perguntas", json={"pergunta": "oi"})

    assert resposta.json() == {"texto": SEM_RESPOSTA, "fontes": [], "respondeu": False}


def test_falha_da_busca_ou_do_modelo_vira_503_com_mensagem_para_a_pessoa():
    async def busca_fora(pergunta, k):
        raise ErroDeBusca("Não consegui falar com o servidor MCP (ConnectError). Ele está no ar?")

    class ModeloFora:
        def responder(self, pergunta, fontes):
            raise ErroDoLLM("Chave da Anthropic inválida. Confira ANTHROPIC_API_KEY.")

    sem_busca = _api(busca_fora).post("/perguntas", json={"pergunta": "oi"})
    sem_modelo = _api(_encontra, ModeloFora()).post("/perguntas", json={"pergunta": "oi"})

    assert (sem_busca.status_code, sem_modelo.status_code) == (503, 503)
    assert "servidor MCP" in sem_busca.json()["detail"]
    assert "Chave da Anthropic inválida" in sem_modelo.json()["detail"]


@pytest.mark.parametrize(
    "corpo", [{}, {"pergunta": ""}, {"pergunta": "x" * 501}, {"pergunta": "oi", "k": 99}]
)
def test_entrada_invalida_e_recusada(corpo):
    assert _api(_encontra).post("/perguntas", json=corpo).status_code == 422


def test_host_desconhecido_e_recusado_e_health_responde():
    api = _api(_encontra)

    assert api.get("/health").json() == {"status": "ok"}
    assert api.get("/health", headers={"host": "malicioso.example"}).status_code == 400
