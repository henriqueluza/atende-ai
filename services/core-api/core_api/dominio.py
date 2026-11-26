"""Conceitos do núcleo. Este arquivo não conhece FastAPI, banco nem serviço externo."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol


class AcervoIndisponivel(Exception):
    """Banco ou serviço de embeddings fora do ar. O detalhe vai para o log, não para o cliente."""


class Visibilidade(StrEnum):
    """Quem pode ver um documento. O agente de atendimento só enxerga PUBLICO."""

    PUBLICO = "publico"
    INTERNO = "interno"


class Situacao(StrEnum):
    """Em que ponto do processamento o documento está. Só INDEXADO aparece na busca."""

    NA_FILA = "na_fila"
    EXTRAINDO = "extraindo"
    INDEXANDO = "indexando"
    INDEXADO = "indexado"
    FALHOU = "falhou"


class Modo(StrEnum):
    """Como a busca compara a pergunta com os trechos. Ver ADR 0007."""

    SEMANTICA = "semantica"  # só o embedding
    PALAVRAS = "palavras"  # só as palavras em comum
    HIBRIDA = "hibrida"  # os dois, somados com peso


@dataclass(frozen=True)
class Documento:
    id: str
    nome: str
    visibilidade: Visibilidade


@dataclass(frozen=True)
class DocumentoNoAcervo:
    """Um documento como aparece na lista de quem administra o acervo."""

    id: str
    nome: str
    visibilidade: Visibilidade
    trechos: int
    criado_em: datetime
    situacao: Situacao = Situacao.INDEXADO
    andamento: str | None = None  # "Lendo a página 2 de 3"
    erro: str | None = None  # por que falhou, em palavras de quem usa
    ocr: bool = False  # alguma parte do texto veio de leitura de imagem
    paginas: int | None = None


@dataclass(frozen=True)
class Trecho:
    """Pedaço de um documento com o vetor (embedding) que representa seu significado."""

    texto: str
    embedding: list[float]
    pagina: int | None = None


@dataclass(frozen=True)
class TrechoGuardado:
    posicao: int
    texto: str
    pagina: int | None


@dataclass(frozen=True)
class ArquivoNaFila:
    """Um arquivo (PDF ou imagem) que espera para ser lido e indexado."""

    documento: Documento
    conteudo: bytes


@dataclass(frozen=True)
class ResultadoBusca:
    trecho: str
    documento: str
    score: float


@dataclass(frozen=True)
class Consulta:
    """Tudo o que o repositório precisa para buscar. `peso` é a parte do embedding na híbrida."""

    pergunta: str
    embedding: list[float]
    k: int
    visibilidade: Visibilidade
    modo: Modo = Modo.SEMANTICA
    peso: float = 0.5


class Embedder(Protocol):
    """Transforma textos em vetores. Textos parecidos geram vetores próximos."""

    dimensao: int

    def gerar(self, textos: list[str]) -> list[list[float]]: ...


class Repositorio(Protocol):
    """Onde documentos e trechos ficam guardados."""

    def salvar(self, documento: Documento, trechos: list[Trecho]) -> None:
        """Guarda o documento já indexado. Se já existir um com o mesmo nome, substitui."""
        ...

    def buscar(self, consulta: Consulta) -> list[ResultadoBusca]:
        """Devolve os k trechos de maior score, só de documentos com a visibilidade pedida."""
        ...

    def listar(self) -> list[DocumentoNoAcervo]:
        """Todos os documentos, públicos e internos, do mais novo para o mais antigo."""
        ...

    def obter(self, id: str) -> DocumentoNoAcervo | None: ...

    def trechos_de(self, id: str) -> list[TrechoGuardado]: ...

    def excluir(self, id: str) -> bool:
        """Apaga o documento e seus trechos. Devolve False se ele não existia."""
        ...

    def alterar_visibilidade(self, id: str, visibilidade: Visibilidade) -> bool: ...

    # --- fila de processamento (PDF e imagem) ---

    def enfileirar(self, documento: Documento, conteudo: bytes) -> None:
        """Guarda o arquivo para processar depois. Substitui o documento de mesmo nome."""
        ...

    def proximo_da_fila(self) -> ArquivoNaFila | None:
        """Pega o arquivo mais antigo da fila e já o marca como EXTRAINDO."""
        ...

    def registrar_andamento(self, id: str, situacao: Situacao, andamento: str | None) -> None: ...

    def concluir(self, id: str, trechos: list[Trecho], ocr: bool, paginas: int | None) -> None:
        """Guarda os trechos e marca INDEXADO. Não faz nada se o documento foi excluído."""
        ...

    def falhar(self, id: str, erro: str) -> None: ...

    def retomar_interrompidos(self) -> int:
        """Devolve à fila o que ficou pela metade quando o serviço parou."""
        ...

    # --- avaliações da busca ---

    def guardar_avaliacao(self, dados: dict[str, Any]) -> None: ...

    def avaliacoes(self) -> list[dict[str, Any]]:
        """Da mais antiga para a mais nova."""
        ...
