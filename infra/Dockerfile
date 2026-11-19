# Uma imagem só para os serviços Python; o comando de cada um vem do docker-compose.yml.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml ./
COPY services ./services
RUN pip install . && useradd --create-home --uid 10001 app

# Nunca rodar como root dentro do container.
USER app
