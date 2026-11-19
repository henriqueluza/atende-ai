"""Repositório em Postgres + pgvector. O filtro de visibilidade fica dentro do SQL."""

import math

import psycopg
from psycopg import sql

from core_api.dominio import AcervoIndisponivel, Documento, ResultadoBusca, Trecho, Visibilidade

_ESQUEMA = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS documentos (
    id uuid PRIMARY KEY,
    nome text NOT NULL UNIQUE,
    visibilidade text NOT NULL CHECK (visibilidade IN ('publico', 'interno')),
    criado_em timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS trechos (
    id bigserial PRIMARY KEY,
    documento_id uuid NOT NULL REFERENCES documentos (id) ON DELETE CASCADE,
    posicao integer NOT NULL,
    texto text NOT NULL,
    embedding vector({dimensao}) NOT NULL
);
"""

# "<=>" é a distância de cosseno do pgvector: 0 = idêntico. O score do contrato é 1 - distância.
_BUSCA = """
SELECT t.texto, d.nome, 1 - (t.embedding <=> %(vetor)s::vector) AS score
FROM trechos t
JOIN documentos d ON d.id = t.documento_id
WHERE d.visibilidade = %(visibilidade)s
ORDER BY t.embedding <=> %(vetor)s::vector
LIMIT %(k)s
"""


class RepositorioPostgres:
    def __init__(self, url: str, dimensao: int) -> None:
        self._url = url
        self._dimensao = dimensao

    def preparar(self) -> None:
        """Cria extensão e tabelas se não existirem. Seguro de chamar a cada início."""
        # DDL não aceita parâmetro (%s), então a dimensão entra pelo compositor do psycopg, que
        # escapa o valor. Ela é um inteiro vindo da configuração do operador, nunca de requisição.
        esquema = sql.SQL(_ESQUEMA).format(dimensao=sql.Literal(int(self._dimensao)))
        with self._conectar() as conexao:
            # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query  # noqa: E501
            conexao.execute(esquema)
            [existente] = conexao.execute(
                "SELECT atttypmod FROM pg_attribute "
                "WHERE attrelid = 'trechos'::regclass AND attname = 'embedding'"
            ).fetchone()
        if existente != self._dimensao:
            raise RuntimeError(
                f"O banco foi criado com embeddings de {existente} dimensões e a configuração "
                f"pede {self._dimensao}. Ajuste EMBEDDINGS_DIM ou recrie o banco e reindexe."
            )

    def salvar(self, documento: Documento, trechos: list[Trecho]) -> None:
        with self._conectar() as conexao:  # uma transação: ou entra tudo, ou nada
            conexao.execute("DELETE FROM documentos WHERE nome = %s", (documento.nome,))
            conexao.execute(
                "INSERT INTO documentos (id, nome, visibilidade) VALUES (%s, %s, %s)",
                (documento.id, documento.nome, documento.visibilidade.value),
            )
            conexao.cursor().executemany(
                "INSERT INTO trechos (documento_id, posicao, texto, embedding) "
                "VALUES (%s, %s, %s, %s::vector)",
                [
                    (documento.id, posicao, trecho.texto, _vetor(trecho.embedding))
                    for posicao, trecho in enumerate(trechos)
                ],
            )

    def buscar(
        self, embedding: list[float], k: int, visibilidade: Visibilidade
    ) -> list[ResultadoBusca]:
        parametros = {"vetor": _vetor(embedding), "visibilidade": visibilidade.value, "k": k}
        with self._conectar() as conexao:
            linhas = conexao.execute(_BUSCA, parametros).fetchall()
        return [ResultadoBusca(texto, nome, _score(score)) for texto, nome, score in linhas]

    def _conectar(self) -> psycopg.Connection:
        try:
            return psycopg.connect(self._url, connect_timeout=5)
        except psycopg.Error as erro:
            raise AcervoIndisponivel("banco de dados") from erro


def _vetor(embedding: list[float]) -> str:
    return "[" + ",".join(repr(float(valor)) for valor in embedding) + "]"


def _score(valor: float) -> float:
    """Limita a 0..1. Vetor sem nenhuma palavra gera NaN no pgvector: vira 0."""
    return max(0.0, min(1.0, valor)) if math.isfinite(valor) else 0.0
