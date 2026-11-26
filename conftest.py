import os
import sys
from pathlib import Path

import psycopg
import pytest

# arquivos_de_teste.py (fábrica de PDFs e imagens) é usado por testes de mais de uma pasta.
sys.path.insert(0, str(Path(__file__).parent / "services" / "core-api" / "tests"))


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
        conexao.execute("DROP TABLE IF EXISTS avaliacoes, arquivos, trechos, documentos")
    return url
