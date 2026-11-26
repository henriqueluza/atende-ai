"""Aplicação HTTP do núcleo. Rode com: uvicorn core_api.main:criar_app --factory"""

import logging
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from core_api.acervo import Acervo, DocumentoVazio
from core_api.config import montar_acervo
from core_api.dominio import AcervoIndisponivel, DocumentoNoAcervo, Modo, Situacao, Visibilidade
from core_api.extracao import TAMANHO_MAXIMO, ErroDeExtracao
from core_api.fila import Trabalhador

log = logging.getLogger("core_api")

NOME = Query(min_length=1, max_length=200, pattern=r"^[^\x00-\x1f/\\]+$")


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


class ArquivoRecebido(BaseModel):
    id: str
    nome: str
    visibilidade: Visibilidade
    situacao: Situacao


class DocumentoListado(BaseModel):
    id: str
    nome: str
    visibilidade: Visibilidade
    trechos: int
    criado_em: datetime
    situacao: Situacao
    andamento: str | None
    erro: str | None
    ocr: bool
    paginas: int | None


class ListaDeDocumentos(BaseModel):
    documentos: list[DocumentoListado]


class TrechoDoDocumento(BaseModel):
    posicao: int
    texto: str
    pagina: int | None


class Passo(BaseModel):
    nome: str
    estado: Literal["feito", "em_andamento", "pendente", "falhou"]
    detalhe: str | None = None
    quando: datetime | None = None


class DetalheDoDocumento(BaseModel):
    documento: DocumentoListado
    trechos: list[TrechoDoDocumento]
    passos: list[Passo]


class NovaVisibilidade(BaseModel):
    visibilidade: Visibilidade


class Resultado(BaseModel):
    trecho: str
    documento: str
    score: float


class RespostaBusca(BaseModel):
    resultados: list[Resultado]


def criar_app(acervo: Acervo | None = None, processar_fila: bool | None = None) -> FastAPI:
    """Sem argumento, monta o acervo a partir das variáveis de ambiente (ver config.py).

    `processar_fila` liga a thread que lê os arquivos enviados. Nos testes ela fica desligada
    e a fila é processada à mão, com `acervo.processar_proximo()`.
    """
    if processar_fila is None:
        processar_fila = acervo is None and os.environ.get("FILA") != "desligada"
    acervo = acervo or montar_acervo()

    @asynccontextmanager
    async def ciclo(_: FastAPI) -> AsyncIterator[None]:
        trabalhador = Trabalhador(acervo) if processar_fila else None
        if trabalhador:
            trabalhador.iniciar()
        yield
        if trabalhador:
            trabalhador.parar()

    app = FastAPI(title="atende-ai core-api", lifespan=ciclo)
    # Recusa requisição com Host desconhecido. Sem isso, uma página maliciosa aberta no
    # navegador de quem roda o sistema poderia alcançar esta API (ataque de DNS rebinding).
    hosts = os.environ.get("CORE_API_HOSTS") or "localhost,127.0.0.1,core-api"
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts.split(","))

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

    @app.post("/documentos/arquivo", status_code=202)
    async def receber_arquivo(
        requisicao: Request,
        nome: Annotated[str, NOME],
        # Sem valor padrão de propósito: quem envia tem que escolher.
        visibilidade: Visibilidade,
    ) -> ArquivoRecebido:
        """Recebe um PDF ou imagem no corpo da requisição e põe na fila de processamento.

        Responde na hora com a situação `na_fila`. O andamento aparece em GET /documentos.
        """
        conteudo = await _ler_corpo(requisicao)
        try:
            # Guardar no banco bloqueia: fora do laço de eventos.
            documento = await run_in_threadpool(
                acervo.receber_arquivo, nome, conteudo, visibilidade
            )
        except ErroDeExtracao as erro:
            raise HTTPException(422, str(erro)) from None
        return ArquivoRecebido(
            id=documento.id,
            nome=documento.nome,
            visibilidade=documento.visibilidade,
            situacao=Situacao.NA_FILA,
        )

    @app.get("/documentos")
    def listar() -> ListaDeDocumentos:
        """Lista para quem administra o acervo: traz também os documentos internos.

        O agente não chega aqui. A única porta dele é o servidor MCP, que só conhece a busca.
        """
        return ListaDeDocumentos(documentos=[_listado(d) for d in acervo.listar()])

    @app.get("/documentos/{id}")
    def detalhar(id: uuid.UUID) -> DetalheDoDocumento:
        detalhe = acervo.detalhar(str(id))
        if detalhe is None:
            raise HTTPException(404, "Documento não encontrado.")
        documento, trechos = detalhe
        return DetalheDoDocumento(
            documento=_listado(documento),
            trechos=[
                TrechoDoDocumento(posicao=t.posicao, texto=t.texto, pagina=t.pagina)
                for t in trechos
            ],
            passos=_passos(documento),
        )

    @app.patch("/documentos/{id}")
    def alterar_visibilidade(id: uuid.UUID, nova: NovaVisibilidade) -> DocumentoListado:
        if not acervo.alterar_visibilidade(str(id), nova.visibilidade):
            raise HTTPException(404, "Documento não encontrado.")
        documento = acervo.repositorio.obter(str(id))
        if documento is None:  # excluído entre uma linha e outra
            raise HTTPException(404, "Documento não encontrado.")
        return _listado(documento)

    @app.delete("/documentos/{id}", status_code=204)
    def excluir(id: uuid.UUID) -> Response:
        if not acervo.excluir(str(id)):
            raise HTTPException(404, "Documento não encontrado.")
        return Response(status_code=204)

    @app.get("/busca")
    def buscar(
        pergunta: Annotated[str, Query(min_length=1, max_length=500)],
        k: Annotated[int, Query(ge=1, le=10)] = 3,
        # Quem não informa a visibilidade só enxerga o que é público.
        visibilidade: Visibilidade = Visibilidade.PUBLICO,
        # Sem `modo`, vale o padrão do servidor (BUSCA_MODO).
        modo: Modo | None = None,
    ) -> RespostaBusca:
        resultados = acervo.buscar(pergunta, k, visibilidade, modo)
        return RespostaBusca(
            resultados=[
                Resultado(trecho=r.trecho, documento=r.documento, score=r.score) for r in resultados
            ]
        )

    return app


async def _ler_corpo(requisicao: Request) -> bytes:
    """Lê o corpo aos poucos e para assim que passar do limite, sem guardar o excesso."""
    declarado = requisicao.headers.get("content-length", "")
    if declarado.isdigit() and int(declarado) > TAMANHO_MAXIMO:
        raise HTTPException(413, "Arquivo grande demais: o limite é 20 MB.")
    partes, total = [], 0
    async for parte in requisicao.stream():
        total += len(parte)
        if total > TAMANHO_MAXIMO:
            raise HTTPException(413, "Arquivo grande demais: o limite é 20 MB.")
        partes.append(parte)
    return b"".join(partes)


def _listado(d: DocumentoNoAcervo) -> DocumentoListado:
    return DocumentoListado(
        id=d.id,
        nome=d.nome,
        visibilidade=d.visibilidade,
        trechos=d.trechos,
        criado_em=d.criado_em,
        situacao=d.situacao,
        andamento=d.andamento,
        erro=d.erro,
        ocr=d.ocr,
        paginas=d.paginas,
    )


def _passos(d: DocumentoNoAcervo) -> list[Passo]:
    """As quatro etapas do processamento e em qual delas o documento está."""
    leitura = "Leitura do texto da imagem (OCR)" if d.ocr else "Extração do texto"
    nomes = ["Arquivo recebido", leitura, "Divisão em trechos", "Indexação para a busca"]
    # Quantas etapas já terminaram. Numa falha, a etapa seguinte é a que falhou: sem trechos,
    # o problema foi ao ler o arquivo.
    feitas = {
        Situacao.NA_FILA: 1,
        Situacao.EXTRAINDO: 1,
        Situacao.INDEXANDO: 3,
        Situacao.INDEXADO: 4,
        Situacao.FALHOU: 1,
    }[d.situacao]
    passos = []
    for indice, nome in enumerate(nomes):
        if indice < feitas:
            detalhe = f"{d.trechos} trecho(s)" if indice == 2 and d.trechos else None
            quando = d.criado_em if indice == 0 else None
            passos.append(Passo(nome=nome, estado="feito", detalhe=detalhe, quando=quando))
        elif indice == feitas and d.situacao == Situacao.FALHOU:
            passos.append(Passo(nome=nome, estado="falhou", detalhe=d.erro))
        elif indice == feitas and d.situacao != Situacao.NA_FILA:
            passos.append(Passo(nome=nome, estado="em_andamento", detalhe=d.andamento))
        else:
            aguardando = "Aguardando a vez na fila" if indice == feitas else None
            passos.append(Passo(nome=nome, estado="pendente", detalhe=aguardando))
    return passos
