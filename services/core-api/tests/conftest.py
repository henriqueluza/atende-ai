import pytest
from core_api.repositorio_memoria import RepositorioMemoria
from core_api.repositorio_postgres import RepositorioPostgres

DIMENSAO = 16


@pytest.fixture(params=["memoria", "postgres"])
def repositorio(request):
    """Cada teste que usa esta fixture roda duas vezes: em memória e no Postgres de verdade."""
    if request.param == "memoria":
        return RepositorioMemoria()
    repositorio = RepositorioPostgres(request.getfixturevalue("url_postgres_limpo"), DIMENSAO)
    repositorio.preparar()
    return repositorio
