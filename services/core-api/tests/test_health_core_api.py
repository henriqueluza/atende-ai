from core_api.config import montar_acervo
from core_api.main import criar_app
from fastapi.testclient import TestClient


def test_health_responde_ok():
    resposta = TestClient(criar_app(montar_acervo({}))).get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}
