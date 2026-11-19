import os

import psycopg
import pytest
from core_api.repositorio_memoria import RepositorioMemoria
from core_api.repositorio_postgres import RepositorioPostgres

DIMENSAO = 16


@pytest.fixture
def url_postgres_limpo():
    """Endereço do banco de teste, já sem tabelas. Pula o teste se não houver banco."""
    url = os.environ.get("DATABASE_URL_TESTE")
    if not url:
        pytest.skip("defina DATABASE_URL_TESTE para rodar contra o Postgres (o CI define)")
    with psycopg.connect(url) as conexao:
        conexao.execute("DROP TABLE IF EXISTS trechos, documentos")
    return url


@pytest.fixture(params=["memoria", "postgres"])
def repositorio(request):
    """Cada teste que usa esta fixture roda duas vezes: em memória e no Postgres de verdade."""
    if request.param == "memoria":
        return RepositorioMemoria()
    repositorio = RepositorioPostgres(request.getfixturevalue("url_postgres_limpo"), DIMENSAO)
    repositorio.preparar()
    return repositorio
