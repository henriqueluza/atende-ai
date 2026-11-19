"""Monta o acervo a partir das variáveis de ambiente. Configuração inválida impede o início."""

import logging
import os

from core_api.acervo import Acervo
from core_api.dominio import Embedder, Repositorio
from core_api.embeddings import EmbedderFalso, EmbedderOpenAI
from core_api.repositorio_memoria import RepositorioMemoria
from core_api.repositorio_postgres import RepositorioPostgres

log = logging.getLogger("core_api")


def montar_acervo(ambiente: dict[str, str] | None = None) -> Acervo:
    ambiente = os.environ if ambiente is None else ambiente
    embedder = _embedder(ambiente)
    return Acervo(_repositorio(ambiente, embedder.dimensao), embedder)


def _embedder(ambiente: dict[str, str]) -> Embedder:
    provedor = ambiente.get("EMBEDDINGS_PROVIDER") or "fake"
    dimensao = int(ambiente.get("EMBEDDINGS_DIM") or 1024)
    if provedor == "fake":
        return EmbedderFalso(dimensao)
    if provedor == "openai":
        modelo, chave = ambiente.get("EMBEDDINGS_MODEL"), ambiente.get("EMBEDDINGS_API_KEY")
        if not modelo or not chave:
            raise RuntimeError(
                "EMBEDDINGS_PROVIDER=openai exige EMBEDDINGS_MODEL e EMBEDDINGS_API_KEY."
            )
        base_url = ambiente.get("EMBEDDINGS_BASE_URL") or "https://api.openai.com/v1"
        return EmbedderOpenAI(base_url, modelo, chave, dimensao)
    raise RuntimeError(f"EMBEDDINGS_PROVIDER desconhecido: {provedor!r}. Use 'fake' ou 'openai'.")


def _repositorio(ambiente: dict[str, str], dimensao: int) -> Repositorio:
    url = ambiente.get("DATABASE_URL")
    if not url:
        log.warning("DATABASE_URL não definida: usando repositório em memória (some no restart).")
        return RepositorioMemoria()
    repositorio = RepositorioPostgres(url, dimensao)
    repositorio.preparar()
    return repositorio
