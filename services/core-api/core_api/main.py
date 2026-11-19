"""Aplicação HTTP do núcleo. Rode com: uvicorn core_api.main:criar_app --factory"""

import logging
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core_api.acervo import Acervo, DocumentoVazio
from core_api.config import montar_acervo
from core_api.dominio import AcervoIndisponivel, Visibilidade

log = logging.getLogger("core_api")


class NovoDocumento(BaseModel):
    nome: str = Field(min_length=1, max_length=200, pattern=r"^[^\x00-\x1f]+$")
    conteudo: str = Field(min_length=1, max_length=1_000_000)
    # Sem valor padrão de propósito: quem envia tem que escolher.
    visibilidade: Visibilidade


class DocumentoIngerido(BaseModel):
    id: str
    nome: str
    visibilidade: Visibilidade
    trechos: int


class Resultado(BaseModel):
    trecho: str
    documento: str
    score: float


class RespostaBusca(BaseModel):
    resultados: list[Resultado]


def criar_app(acervo: Acervo | None = None) -> FastAPI:
    """Sem argumento, monta o acervo a partir das variáveis de ambiente (ver config.py)."""
    acervo = acervo or montar_acervo()
    app = FastAPI(title="atende-ai core-api")

    @app.exception_handler(AcervoIndisponivel)
    def indisponivel(_: Request, erro: AcervoIndisponivel) -> JSONResponse:
        # O detalhe fica no log. Para fora vai só uma mensagem genérica.
        log.error("Dependência fora do ar: %s", erro, exc_info=erro)
        return JSONResponse({"detail": "Serviço temporariamente indisponível."}, status_code=503)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Usado pelo docker compose para saber se o serviço está de pé."""
        return {"status": "ok"}

    @app.post("/documentos", status_code=201)
    def ingerir(novo: NovoDocumento) -> DocumentoIngerido:
        try:
            documento, trechos = acervo.ingerir(novo.nome, novo.conteudo, novo.visibilidade)
        except DocumentoVazio:
            raise HTTPException(422, "O documento não tem texto para indexar.") from None
        return DocumentoIngerido(
            id=documento.id,
            nome=documento.nome,
            visibilidade=documento.visibilidade,
            trechos=trechos,
        )

    @app.get("/busca")
    def buscar(
        pergunta: Annotated[str, Query(min_length=1, max_length=500)],
        k: Annotated[int, Query(ge=1, le=10)] = 3,
        # Quem não informa a visibilidade só enxerga o que é público.
        visibilidade: Visibilidade = Visibilidade.PUBLICO,
    ) -> RespostaBusca:
        resultados = acervo.buscar(pergunta, k, visibilidade)
        return RespostaBusca(
            resultados=[
                Resultado(trecho=r.trecho, documento=r.documento, score=r.score) for r in resultados
            ]
        )

    return app
