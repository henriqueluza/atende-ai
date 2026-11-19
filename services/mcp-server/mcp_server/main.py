"""Servidor MCP por Streamable HTTP. Rode com: uvicorn mcp_server.main:app

As ferramentas ficam em /mcp. O contrato delas está em services/mcp-server/README.md.
"""

from mcp.server.mcpserver import MCPServer
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse


def criar_servidor() -> MCPServer:
    servidor = MCPServer(
        "atende-ai",
        instructions="Ferramentas do acervo de conhecimento do negócio (somente conteúdo público).",
    )

    @servidor.custom_route("/health", methods=["GET"])
    async def health(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return servidor


def criar_app() -> Starlette:
    # Sem estado entre chamadas e resposta em JSON: é o modo mais simples de operar e testar.
    return criar_servidor().streamable_http_app(stateless_http=True, json_response=True)


app = criar_app()
