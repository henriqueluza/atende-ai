"""Conceitos do núcleo. Este arquivo não conhece FastAPI, banco nem serviço externo."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class Visibilidade(StrEnum):
    """Quem pode ver um documento. O agente de atendimento só enxerga PUBLICO."""

    PUBLICO = "publico"
    INTERNO = "interno"


@dataclass(frozen=True)
class Documento:
    id: str
    nome: str
    visibilidade: Visibilidade


@dataclass(frozen=True)
class Trecho:
    """Pedaço de um documento com o vetor (embedding) que representa seu significado."""

    texto: str
    embedding: list[float]


@dataclass(frozen=True)
class ResultadoBusca:
    trecho: str
    documento: str
    score: float


class Embedder(Protocol):
    """Transforma textos em vetores. Textos parecidos geram vetores próximos."""

    dimensao: int

    def gerar(self, textos: list[str]) -> list[list[float]]: ...


class Repositorio(Protocol):
    """Onde documentos e trechos ficam guardados."""

    def salvar(self, documento: Documento, trechos: list[Trecho]) -> None:
        """Guarda o documento. Se já existir um com o mesmo nome, substitui."""
        ...

    def buscar(
        self, embedding: list[float], k: int, visibilidade: Visibilidade
    ) -> list[ResultadoBusca]:
        """Devolve os k trechos mais parecidos, só de documentos com a visibilidade pedida."""
        ...
