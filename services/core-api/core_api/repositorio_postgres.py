"""Repositório em Postgres + pgvector. O filtro de visibilidade fica dentro do SQL."""

import json
import math
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg import sql

from core_api.dominio import (
    AcervoIndisponivel,
    ArquivoNaFila,
    Consulta,
    Documento,
    DocumentoNoAcervo,
    Modo,
    ResultadoBusca,
    Situacao,
    Trecho,
    TrechoGuardado,
    Visibilidade,
)

# Texto em minúsculas e sem acento, para a busca por palavras: cliente escreve "horario".
# É uma expressão imutável, por isso pode alimentar uma coluna gerada.
_NORMAL = "translate(lower({}), 'áàâãäéèêëíìîïóòôõöúùûüçñ', 'aaaaaeeeeiiiiooooouuuucn')"

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
    "ALTER TABLE trechos ADD COLUMN IF NOT EXISTS palavras tsvector GENERATED ALWAYS AS "
    f"(to_tsvector('portuguese', {_NORMAL.format('texto')})) STORED",
    "CREATE INDEX IF NOT EXISTS trechos_palavras ON trechos USING gin (palavras)",
    "CREATE INDEX IF NOT EXISTS trechos_documento ON trechos (documento_id)",
    # O arquivo original fica guardado só enquanto espera na fila.
    """CREATE TABLE IF NOT EXISTS arquivos (
        documento_id uuid PRIMARY KEY REFERENCES documentos (id) ON DELETE CASCADE,
        conteudo bytea NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS avaliacoes (
        id bigserial PRIMARY KEY,
        criado_em timestamptz NOT NULL DEFAULT now(),
        dados jsonb NOT NULL
    )""",
]

# Índice aproximado (HNSW) para a busca por vetor. O pgvector só indexa até 2000 dimensões.
_INDICE_VETORIAL = (
    "CREATE INDEX IF NOT EXISTS trechos_embedding "
    "ON trechos USING hnsw (embedding vector_cosine_ops)"
)
_DIMENSAO_MAXIMA_DO_INDICE = 2000

# Uma consulta só para os três modos. "<=>" é a distância de cosseno do pgvector (0 = idêntico).
# 1. `pergunta`: as palavras da pergunta já no radical, pelo dicionário de português.
# 2. `candidatos`: os mais próximos pelo vetor (usa o índice HNSW) e os que têm alguma palavra
#    da pergunta (usa o índice GIN). O filtro de visibilidade está nas duas metades.
# 3. Para cada candidato, as duas notas exatas: semelhança do vetor e cobertura, que é a fração
#    das palavras da pergunta presentes no trecho.
# A pergunta passa pela mesma normalização de _NORMAL, escrita aqui por extenso para a
# consulta ser um texto fixo.
_BUSCA = """
WITH pergunta AS (
    SELECT coalesce(array_agg(lexema), '{}') AS lexemas
    FROM unnest(tsvector_to_array(to_tsvector('portuguese',
        translate(lower(%(pergunta)s), 'áàâãäéèêëíìîïóòôõöúùûüçñ', 'aaaaaeeeeiiiiooooouuuucn')
    ))) AS lexema
    WHERE lexema ~ '^[a-z0-9]+$'
),
candidatos AS (
    (SELECT t.id FROM trechos t JOIN documentos d ON d.id = t.documento_id
     WHERE d.visibilidade = %(visibilidade)s AND %(usa_vetor)s
     ORDER BY t.embedding <=> %(vetor)s::vector LIMIT %(candidatos)s)
    UNION
    (SELECT t.id FROM trechos t JOIN documentos d ON d.id = t.documento_id, pergunta p
     WHERE d.visibilidade = %(visibilidade)s AND %(usa_palavras)s
       AND cardinality(p.lexemas) > 0
       AND t.palavras @@ to_tsquery('simple', array_to_string(p.lexemas, ' | '))
     LIMIT %(candidatos)s)
),
notas AS (
    SELECT t.texto, d.nome, t.id,
        1 - (t.embedding <=> %(vetor)s::vector) AS semantica,
        CASE WHEN cardinality(p.lexemas) = 0 THEN 0 ELSE
            (SELECT count(*) FROM unnest(p.lexemas) AS lexema
             WHERE lexema = ANY (tsvector_to_array(t.palavras)))::float8 / cardinality(p.lexemas)
        END AS cobertura
    FROM candidatos c
    JOIN trechos t ON t.id = c.id
    JOIN documentos d ON d.id = t.documento_id
    CROSS JOIN pergunta p
    -- De novo, de propósito: nenhum trecho sai daqui sem conferir a visibilidade.
    WHERE d.visibilidade = %(visibilidade)s
)
SELECT texto, nome, semantica, cobertura FROM notas
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
            if existente == self._dimensao and self._dimensao <= _DIMENSAO_MAXIMA_DO_INDICE:
                conexao.execute(_INDICE_VETORIAL)
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
            "pergunta": consulta.pergunta,
            "vetor": _vetor(consulta.embedding),
            "visibilidade": consulta.visibilidade.value,
            "usa_vetor": consulta.modo != Modo.PALAVRAS,
            "usa_palavras": consulta.modo != Modo.SEMANTICA,
            # Na híbrida, busca mais candidatos do que vai devolver: a ordem final muda.
            "candidatos": consulta.k
            if consulta.modo == Modo.SEMANTICA
            else max(4 * consulta.k, 20),
        }
        with self._conexao() as conexao:
            # Com filtro de visibilidade, o índice aproximado pode devolver menos que o pedido.
            # A varredura iterativa (pgvector 0.8+) continua procurando até completar.
            conexao.execute("SET LOCAL hnsw.iterative_scan = relaxed_order")
            linhas = conexao.execute(_BUSCA, parametros).fetchall()
        resultados = [
            ResultadoBusca(texto, nome, _nota(consulta, semantica, cobertura))
            for texto, nome, semantica, cobertura in linhas
        ]
        if consulta.modo == Modo.PALAVRAS:
            resultados = [resultado for resultado in resultados if resultado.score > 0]
        return sorted(resultados, key=lambda r: r.score, reverse=True)[: consulta.k]

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

    def guardar_avaliacao(self, dados: dict[str, Any]) -> None:
        with self._conexao() as conexao:
            conexao.execute(
                "INSERT INTO avaliacoes (dados) VALUES (%s::jsonb)", (json.dumps(dados),)
            )

    def avaliacoes(self) -> list[dict[str, Any]]:
        with self._conexao() as conexao:
            linhas = conexao.execute("SELECT dados FROM avaliacoes ORDER BY id").fetchall()
        return [dados for (dados,) in linhas]

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


def _nota(consulta: Consulta, semantica: float, cobertura: float) -> float:
    semantica = _limitar(semantica)
    if consulta.modo == Modo.SEMANTICA:
        return semantica
    if consulta.modo == Modo.PALAVRAS:
        return _limitar(cobertura)
    return consulta.peso * semantica + (1 - consulta.peso) * _limitar(cobertura)


def _vetor(embedding: list[float]) -> str:
    return "[" + ",".join(repr(float(valor)) for valor in embedding) + "]"


def _limitar(valor: float) -> float:
    """Limita a 0..1. Vetor sem nenhuma palavra gera NaN no pgvector: vira 0."""
    return max(0.0, min(1.0, valor)) if math.isfinite(valor) else 0.0
