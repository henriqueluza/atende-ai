"""Repositório em Postgres + pgvector. O filtro de visibilidade fica dentro do SQL."""

import math
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg import sql

from core_api.dominio import (
    AcervoIndisponivel,
    ArquivoNaFila,
    Consulta,
    Documento,
    DocumentoNoAcervo,
    ResultadoBusca,
    Situacao,
    Trecho,
    TrechoGuardado,
    Visibilidade,
)

# Cada comando roda sozinho, e todos podem ser repetidos: é assim que um banco criado na
# Etapa 1 ganha as colunas novas sem perder os dados.
_ESQUEMA = [
    "CREATE EXTENSION IF NOT EXISTS vector",
    """CREATE TABLE IF NOT EXISTS documentos (
        id uuid PRIMARY KEY,
        nome text NOT NULL UNIQUE,
        visibilidade text NOT NULL CHECK (visibilidade IN ('publico', 'interno')),
        criado_em timestamptz NOT NULL DEFAULT now()
    )""",
    "ALTER TABLE documentos ADD COLUMN IF NOT EXISTS situacao text NOT NULL DEFAULT 'indexado'",
    "ALTER TABLE documentos ADD COLUMN IF NOT EXISTS andamento text",
    "ALTER TABLE documentos ADD COLUMN IF NOT EXISTS erro text",
    "ALTER TABLE documentos ADD COLUMN IF NOT EXISTS ocr boolean NOT NULL DEFAULT false",
    "ALTER TABLE documentos ADD COLUMN IF NOT EXISTS paginas integer",
    """CREATE TABLE IF NOT EXISTS trechos (
        id bigserial PRIMARY KEY,
        documento_id uuid NOT NULL REFERENCES documentos (id) ON DELETE CASCADE,
        posicao integer NOT NULL,
        texto text NOT NULL,
        embedding vector({dimensao}) NOT NULL
    )""",
    "ALTER TABLE trechos ADD COLUMN IF NOT EXISTS pagina integer",
    "CREATE INDEX IF NOT EXISTS trechos_documento ON trechos (documento_id)",
    # O arquivo original fica guardado só enquanto espera na fila.
    """CREATE TABLE IF NOT EXISTS arquivos (
        documento_id uuid PRIMARY KEY REFERENCES documentos (id) ON DELETE CASCADE,
        conteudo bytea NOT NULL
    )""",
]

# "<=>" é a distância de cosseno do pgvector: 0 = idêntico. O score do contrato é 1 - distância.
_BUSCA = """
SELECT t.texto, d.nome, 1 - (t.embedding <=> %(vetor)s::vector) AS score
FROM trechos t
JOIN documentos d ON d.id = t.documento_id
WHERE d.visibilidade = %(visibilidade)s
ORDER BY t.embedding <=> %(vetor)s::vector
LIMIT %(k)s
"""

# A ficha de um documento, com a contagem de trechos. São duas consultas escritas por
# extenso, sem montar texto de SQL em tempo de execução.
_LISTA = """
SELECT d.id::text, d.nome, d.visibilidade, count(t.id), d.criado_em,
       d.situacao, d.andamento, d.erro, d.ocr, d.paginas
FROM documentos d
LEFT JOIN trechos t ON t.documento_id = d.id
GROUP BY d.id
ORDER BY d.criado_em DESC, d.nome
"""

_UM_DOCUMENTO = """
SELECT d.id::text, d.nome, d.visibilidade, count(t.id), d.criado_em,
       d.situacao, d.andamento, d.erro, d.ocr, d.paginas
FROM documentos d
LEFT JOIN trechos t ON t.documento_id = d.id
WHERE d.id = %s
GROUP BY d.id
"""

# Pega o mais antigo da fila. SKIP LOCKED deixa dois processos trabalharem sem pegar o mesmo.
_PROXIMO = """
UPDATE documentos SET situacao = 'extraindo', andamento = NULL
WHERE id = (
    SELECT id FROM documentos WHERE situacao = 'na_fila'
    ORDER BY criado_em LIMIT 1 FOR UPDATE SKIP LOCKED
)
RETURNING id::text, nome, visibilidade
"""


class RepositorioPostgres:
    def __init__(self, url: str, dimensao: int) -> None:
        self._url = url
        self._dimensao = dimensao

    def preparar(self) -> None:
        """Cria extensão, tabelas e colunas que faltarem. Seguro de chamar a cada início."""
        with self._conexao() as conexao:
            for comando in _ESQUEMA:
                # DDL não aceita parâmetro (%s), então a dimensão entra pelo compositor do
                # psycopg, que escapa o valor. Ela é um inteiro vindo da configuração do
                # operador, nunca de requisição.
                if "{dimensao}" in comando:
                    comando = sql.SQL(comando).format(dimensao=sql.Literal(int(self._dimensao)))
                # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query  # noqa: E501
                conexao.execute(comando)
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
        with self._conexao() as conexao:  # uma transação: ou entra tudo, ou nada
            self._inserir(conexao, documento, Situacao.INDEXADO)
            self._inserir_trechos(conexao, documento.id, trechos)

    def buscar(self, consulta: Consulta) -> list[ResultadoBusca]:
        parametros = {
            "vetor": _vetor(consulta.embedding),
            "visibilidade": consulta.visibilidade.value,
            "k": consulta.k,
        }
        with self._conexao() as conexao:
            linhas = conexao.execute(_BUSCA, parametros).fetchall()
        return [ResultadoBusca(texto, nome, _limitar(score)) for texto, nome, score in linhas]

    def listar(self) -> list[DocumentoNoAcervo]:
        with self._conexao() as conexao:
            linhas = conexao.execute(_LISTA).fetchall()
        return [_ficha(linha) for linha in linhas]

    def obter(self, id: str) -> DocumentoNoAcervo | None:
        with self._conexao() as conexao:
            linha = conexao.execute(_UM_DOCUMENTO, (id,)).fetchone()
        return _ficha(linha) if linha else None

    def trechos_de(self, id: str) -> list[TrechoGuardado]:
        with self._conexao() as conexao:
            linhas = conexao.execute(
                "SELECT posicao, texto, pagina FROM trechos "
                "WHERE documento_id = %s ORDER BY posicao",
                (id,),
            ).fetchall()
        return [TrechoGuardado(posicao, texto, pagina) for posicao, texto, pagina in linhas]

    def excluir(self, id: str) -> bool:
        with self._conexao() as conexao:  # trechos e arquivo saem junto (ON DELETE CASCADE)
            return conexao.execute("DELETE FROM documentos WHERE id = %s", (id,)).rowcount > 0

    def alterar_visibilidade(self, id: str, visibilidade: Visibilidade) -> bool:
        with self._conexao() as conexao:
            comando = "UPDATE documentos SET visibilidade = %s WHERE id = %s"
            return conexao.execute(comando, (visibilidade.value, id)).rowcount > 0

    def enfileirar(self, documento: Documento, conteudo: bytes) -> None:
        with self._conexao() as conexao:
            self._inserir(conexao, documento, Situacao.NA_FILA)
            conexao.execute(
                "INSERT INTO arquivos (documento_id, conteudo) VALUES (%s, %s)",
                (documento.id, conteudo),
            )

    def proximo_da_fila(self) -> ArquivoNaFila | None:
        with self._conexao() as conexao:
            linha = conexao.execute(_PROXIMO).fetchone()
            if linha is None:
                return None
            id, nome, visibilidade = linha
            arquivo = conexao.execute(
                "SELECT conteudo FROM arquivos WHERE documento_id = %s", (id,)
            ).fetchone()
        conteudo = bytes(arquivo[0]) if arquivo else b""
        return ArquivoNaFila(Documento(id, nome, Visibilidade(visibilidade)), conteudo)

    def registrar_andamento(self, id: str, situacao: Situacao, andamento: str | None) -> None:
        with self._conexao() as conexao:
            conexao.execute(
                "UPDATE documentos SET situacao = %s, andamento = %s WHERE id = %s",
                (situacao.value, andamento, id),
            )

    def concluir(self, id: str, trechos: list[Trecho], ocr: bool, paginas: int | None) -> None:
        with self._conexao() as conexao:
            atualizado = conexao.execute(
                "UPDATE documentos SET situacao = 'indexado', andamento = NULL, erro = NULL, "
                "ocr = %s, paginas = %s WHERE id = %s",
                (ocr, paginas, id),
            )
            if atualizado.rowcount == 0:
                return  # excluído enquanto era processado
            conexao.execute("DELETE FROM trechos WHERE documento_id = %s", (id,))
            conexao.execute("DELETE FROM arquivos WHERE documento_id = %s", (id,))
            self._inserir_trechos(conexao, id, trechos)

    def falhar(self, id: str, erro: str) -> None:
        with self._conexao() as conexao:
            conexao.execute(
                "UPDATE documentos SET situacao = 'falhou', andamento = NULL, erro = %s "
                "WHERE id = %s",
                (erro, id),
            )

    def retomar_interrompidos(self) -> int:
        with self._conexao() as conexao:
            return conexao.execute(
                "UPDATE documentos SET situacao = 'na_fila', andamento = NULL "
                "WHERE situacao IN ('extraindo', 'indexando')"
            ).rowcount

    @staticmethod
    def _inserir(conexao: psycopg.Connection, documento: Documento, situacao: Situacao) -> None:
        conexao.execute("DELETE FROM documentos WHERE nome = %s", (documento.nome,))
        conexao.execute(
            "INSERT INTO documentos (id, nome, visibilidade, situacao) VALUES (%s, %s, %s, %s)",
            (documento.id, documento.nome, documento.visibilidade.value, situacao.value),
        )

    @staticmethod
    def _inserir_trechos(conexao: psycopg.Connection, id: str, trechos: list[Trecho]) -> None:
        conexao.cursor().executemany(
            "INSERT INTO trechos (documento_id, posicao, texto, embedding, pagina) "
            "VALUES (%s, %s, %s, %s::vector, %s)",
            [
                (id, posicao, trecho.texto, _vetor(trecho.embedding), trecho.pagina)
                for posicao, trecho in enumerate(trechos)
            ],
        )

    @contextmanager
    def _conexao(self) -> Iterator[psycopg.Connection]:
        """Abre uma transação. Qualquer falha do banco vira AcervoIndisponivel (HTTP 503)."""
        try:
            with psycopg.connect(self._url, connect_timeout=5) as conexao:
                yield conexao
        except psycopg.Error as erro:
            raise AcervoIndisponivel("banco de dados") from erro


def _ficha(linha: tuple) -> DocumentoNoAcervo:
    id, nome, visibilidade, trechos, criado_em, situacao, andamento, erro, ocr, paginas = linha
    return DocumentoNoAcervo(
        id,
        nome,
        Visibilidade(visibilidade),
        trechos,
        criado_em,
        Situacao(situacao),
        andamento,
        erro,
        ocr,
        paginas,
    )


def _vetor(embedding: list[float]) -> str:
    return "[" + ",".join(repr(float(valor)) for valor in embedding) + "]"


def _limitar(valor: float) -> float:
    """Limita a 0..1. Vetor sem nenhuma palavra gera NaN no pgvector: vira 0."""
    return max(0.0, min(1.0, valor)) if math.isfinite(valor) else 0.0
