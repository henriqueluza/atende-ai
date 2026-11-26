import pytest
from core_api.acervo import Acervo
from core_api.avaliacao import PerguntaDeTeste, avaliar
from core_api.dominio import Modo, Visibilidade
from core_api.embeddings import EmbedderFalso
from core_api.main import criar_app
from core_api.repositorio_memoria import RepositorioMemoria
from fastapi.testclient import TestClient

PERGUNTAS = [
    {"pergunta": "Qual o horário de funcionamento?", "esperado": "faq.md"},
    {"pergunta": "Quanto custa a manicure?", "esperado": "precos.md"},
    {"pergunta": "Vocês vendem pão de queijo?", "esperado": "cardapio.md"},
]


@pytest.fixture
def acervo():
    acervo = Acervo(RepositorioMemoria(), EmbedderFalso(256))
    acervo.ingerir("faq.md", "## Horário de funcionamento\n\nDas 9h às 19h.", Visibilidade.PUBLICO)
    acervo.ingerir("precos.md", "## Unhas\n\nManicure custa R$ 35.", Visibilidade.PUBLICO)
    acervo.ingerir("custos.md", "## Custo da manicure\n\nR$ 9.", Visibilidade.INTERNO)
    return acervo


def test_avaliar_conta_acertos_posicao_e_mrr(acervo):
    perguntas = [PerguntaDeTeste(**p) for p in PERGUNTAS]

    execucao = avaliar(acervo, perguntas, k=1, modo=Modo.HIBRIDA, versao="abc123")

    assert (execucao["perguntas"], execucao["acertos"]) == (3, 2)
    assert execucao["mrr"] == pytest.approx(2 / 3, abs=0.001)
    assert [(d["posicao"], d["primeiro"]) for d in execucao["detalhe"][:2]] == [
        (1, "faq.md"),
        (1, "precos.md"),
    ]
    assert execucao["detalhe"][2]["posicao"] is None
    # A avaliação usa a busca pública: documento interno nunca aparece nela.
    assert all(d["primeiro"] != "custos.md" for d in execucao["detalhe"])


def test_api_guarda_as_execucoes_e_repete_o_ultimo_conjunto(acervo):
    api = TestClient(criar_app(acervo), base_url="http://localhost")

    assert api.get("/avaliacao").json() == {"k": 3, "execucoes": [], "perguntas": []}
    assert api.post("/avaliacao/execucoes", json={}).status_code == 422  # ainda sem conjunto

    primeira = api.post(
        "/avaliacao/execucoes", json={"perguntas": PERGUNTAS, "versao": "abc123", "nota": "Início"}
    )
    acervo.ingerir("cardapio.md", "## Lanches\n\nVendemos pão de queijo.", Visibilidade.PUBLICO)
    segunda = api.post("/avaliacao/execucoes", json={"versao": "def456"})
    historico = api.get("/avaliacao").json()

    assert (primeira.status_code, primeira.json()["acertos"]) == (201, 2)
    assert segunda.json()["acertos"] == 3
    assert [(e["versao"], e["acertos"]) for e in historico["execucoes"]] == [
        ("abc123", 2),
        ("def456", 3),
    ]
    assert len(historico["perguntas"]) == 3 and historico["perguntas"][2]["posicao"] == 1


def test_api_recusa_versao_com_caracteres_estranhos(acervo):
    api = TestClient(criar_app(acervo), base_url="http://localhost")
    corpo = {"perguntas": PERGUNTAS, "versao": "<script>"}

    assert api.post("/avaliacao/execucoes", json=corpo).status_code == 422
