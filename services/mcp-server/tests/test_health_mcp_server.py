from mcp_server.main import criar_app
from starlette.testclient import TestClient


def test_health_responde_ok():
    with TestClient(criar_app()) as cliente:
        resposta = cliente.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_so_atende_host_conhecido():
    chamada = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    cabecalhos = {"accept": "application/json, text/event-stream"}

    with TestClient(criar_app(), base_url="http://mcp-server:8001") as do_compose:
        aceito = do_compose.post("/mcp", json=chamada, headers=cabecalhos)
    with TestClient(criar_app(), base_url="http://malicioso.example") as de_fora:
        recusado = de_fora.post("/mcp", json=chamada, headers=cabecalhos)

    assert aceito.status_code == 200
    assert recusado.status_code == 421
