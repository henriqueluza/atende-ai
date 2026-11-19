"""Monta o sistema inteiro dentro do processo de teste, sem Docker e sem chave de API.

As peças são as de produção: a aplicação do core-api, o servidor MCP e o agente. Só o
"fio" entre elas muda: em vez de rede, chamadas diretas em memória.
"""

from dataclasses import dataclass

import httpx
import pytest
from agent.atendente import Buscar, busca_por_mcp
from core_api.acervo import Acervo
from core_api.embeddings import EmbedderFalso
from core_api.main import criar_app
from core_api.repositorio_memoria import RepositorioMemoria
from core_api.repositorio_postgres import RepositorioPostgres
from fastapi.testclient import TestClient
from mcp.server.mcpserver import MCPServer
from mcp_server.main import criar_servidor


@dataclass
class Sistema:
    core_api: TestClient  # para ingerir, como o `ingest` faz
    mcp: MCPServer  # o servidor MCP de verdade, ligado ao core-api acima
    buscar: Buscar  # a busca do agente, passando pelo servidor MCP


@pytest.fixture(params=["memoria", "postgres"])
def sistema(request) -> Sistema:
    """Cada teste roda duas vezes: com o acervo em memória e no Postgres + pgvector."""
    embedder = EmbedderFalso()
    if request.param == "memoria":
        repositorio = RepositorioMemoria()
    else:
        url = request.getfixturevalue("url_postgres_limpo")
        repositorio = RepositorioPostgres(url, embedder.dimensao)
        repositorio.preparar()
    app = criar_app(Acervo(repositorio, embedder))
    para_o_core_api = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://core-api"
    )
    mcp = criar_servidor(para_o_core_api)
    return Sistema(core_api=TestClient(app), mcp=mcp, buscar=busca_por_mcp(mcp))
