"""Aplicação HTTP do núcleo. Rode com: uvicorn core_api.main:app"""

from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from core_api.acervo import Acervo, DocumentoVazio
from core_api.dominio import Visibilidade
from core_api.embeddings import EmbedderFalso
from core_api.repositorio_memoria import RepositorioMemoria


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
    acervo = acervo or Acervo(RepositorioMemoria(), EmbedderFalso())
    app = FastAPI(title="atende-ai core-api")

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


app = criar_app()
