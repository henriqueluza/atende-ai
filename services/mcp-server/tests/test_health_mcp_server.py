from mcp_server.main import criar_app
from starlette.testclient import TestClient


def test_health_responde_ok():
    with TestClient(criar_app()) as cliente:
        resposta = cliente.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}
