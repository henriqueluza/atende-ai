"""Aplicação HTTP do núcleo. Rode com: uvicorn core_api.main:app"""

from fastapi import FastAPI

app = FastAPI(title="atende-ai core-api")


@app.get("/health")
def health() -> dict[str, str]:
    """Usado pelo docker compose para saber se o serviço está de pé."""
    return {"status": "ok"}
