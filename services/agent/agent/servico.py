"""O atendente por HTTP. Rode com: uvicorn agent.servico:criar_app --factory

É o mesmo fluxo do `ask` do terminal (busca pelo servidor MCP, só conteúdo público, e o LLM
redige). Serve o aplicativo de desktop hoje e vai servir o WhatsApp na Etapa 3.
"""

import logging
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from agent.atendente import SCORE_MINIMO, Buscar, ErroDeBusca, busca_por_mcp
from agent.cli import carregar_env, escolher_llm
from agent.llm import LLM, SEM_RESPOSTA, ErroDoLLM

log = logging.getLogger("agent")


class Pergunta(BaseModel):
    pergunta: str = Field(min_length=1, max_length=500)
    k: int = Field(default=3, ge=1, le=10)


class FonteUsada(BaseModel):
    trecho: str
    documento: str
    score: float


class RespostaDoAtendente(BaseModel):
    texto: str
    fontes: list[FonteUsada]
    respondeu: bool  # False: o atendente disse que não encontrou a informação


def criar_app(buscar: Buscar | None = None, llm: LLM | None = None) -> FastAPI:
    """Sem argumentos, lê a configuração do ambiente (as mesmas variáveis do terminal)."""
    carregar_env()
    buscar = buscar or busca_por_mcp(
        os.environ.get("MCP_SERVER_URL") or "http://localhost:8001/mcp"
    )
    llm = llm or escolher_llm()  # configuração inválida impede o início
    score_minimo = float(os.environ.get("SCORE_MINIMO") or SCORE_MINIMO)

    app = FastAPI(title="atende-ai agente")
    hosts = os.environ.get("AGENT_HOSTS") or "localhost,127.0.0.1,agent"
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts.split(","))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/perguntas")
    async def perguntar(nova: Pergunta) -> RespostaDoAtendente:
        try:
            encontradas = await buscar(nova.pergunta, nova.k)
            fontes = [fonte for fonte in encontradas if fonte.score >= score_minimo]
            if not fontes:
                # Sem trecho relevante, nem chama o modelo: melhor dizer que não sabe.
                return RespostaDoAtendente(texto=SEM_RESPOSTA, fontes=[], respondeu=False)
            # A chamada ao modelo bloqueia: roda fora do laço de eventos.
            texto = await run_in_threadpool(llm.responder, nova.pergunta, fontes)
        except (ErroDeBusca, ErroDoLLM) as erro:
            # A mensagem dessas exceções já é própria para mostrar e não traz segredo.
            log.error("Falha ao responder: %s", type(erro).__name__)
            raise HTTPException(503, str(erro)) from None
        return RespostaDoAtendente(
            texto=texto,
            fontes=[
                FonteUsada(trecho=f.trecho, documento=f.documento, score=f.score) for f in fontes
            ],
            respondeu=texto.strip() != SEM_RESPOSTA,
        )

    return app
