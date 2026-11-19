# infra

Docker e configuração de deploy.

## Como usar

```bash
cp .env.example .env      # na raiz do repositório
docker compose up -d      # sobe db (Postgres + pgvector), core-api e mcp-server
docker compose ps         # os três devem aparecer como "healthy"
docker compose down       # derruba (acrescente -v para apagar os dados do banco)
```

- `Dockerfile`: uma imagem só para os serviços Python; o comando de cada serviço está no `docker-compose.yml` da raiz.
- As portas ficam presas em `127.0.0.1` (core-api em 8000, mcp-server em 8001, banco em 5432). Para mudar, edite o `.env`.
- O CI (`.github/workflows/ci.yml`) instala o projeto com `pip install -e ".[dev]"` e sobe um Postgres + pgvector próprio para os testes.
