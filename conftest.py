import os

import psycopg
import pytest


@pytest.fixture
def anyio_backend():
    """Faz os testes marcados com @pytest.mark.anyio rodarem em asyncio."""
    return "asyncio"


@pytest.fixture
def url_postgres_limpo():
    """Endereço do banco de teste, já sem tabelas. Pula o teste se não houver banco."""
    url = os.environ.get("DATABASE_URL_TESTE")
    if not url:
        pytest.skip("defina DATABASE_URL_TESTE para rodar contra o Postgres (o CI define)")
    with psycopg.connect(url) as conexao:
        conexao.execute("DROP TABLE IF EXISTS trechos, documentos")
    return url
