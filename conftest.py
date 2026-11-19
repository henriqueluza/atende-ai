import pytest


@pytest.fixture
def anyio_backend():
    """Faz os testes marcados com @pytest.mark.anyio rodarem em asyncio."""
    return "asyncio"
