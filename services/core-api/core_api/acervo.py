"""Casos de uso do núcleo: ingerir um documento e buscar no acervo."""

import uuid

from core_api.chunking import dividir_em_trechos
from core_api.dominio import (
    Documento,
    Embedder,
    Repositorio,
    ResultadoBusca,
    Trecho,
    Visibilidade,
)


class DocumentoVazio(ValueError):
    """O conteúdo enviado não tem texto para indexar."""


class Acervo:
    def __init__(self, repositorio: Repositorio, embedder: Embedder) -> None:
        self._repositorio = repositorio
        self._embedder = embedder

    def ingerir(
        self, nome: str, conteudo: str, visibilidade: Visibilidade
    ) -> tuple[Documento, int]:
        """Divide, gera os embeddings e guarda. Devolve o documento e quantos trechos gerou."""
        textos = dividir_em_trechos(conteudo)
        if not textos:
            raise DocumentoVazio(nome)
        embeddings = self._embedder.gerar(textos)
        trechos = [Trecho(t, e) for t, e in zip(textos, embeddings, strict=True)]
        documento = Documento(id=str(uuid.uuid4()), nome=nome, visibilidade=visibilidade)
        self._repositorio.salvar(documento, trechos)
        return documento, len(trechos)

    def buscar(self, pergunta: str, k: int, visibilidade: Visibilidade) -> list[ResultadoBusca]:
        [embedding] = self._embedder.gerar([pergunta])
        return self._repositorio.buscar(embedding, k, visibilidade)
