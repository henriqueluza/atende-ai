# core-api

Núcleo da plataforma: recebe documentos, divide em trechos, indexa e responde buscas.

## Como usar

Com o sistema no ar (`docker compose up -d`), a API fica em `http://localhost:8000` (documentação interativa em `/docs`).

```bash
# Enviar um documento (texto ou markdown). A visibilidade é obrigatória.
curl -X POST localhost:8000/documentos -H 'content-type: application/json' \
  -d '{"nome": "faq.md", "conteudo": "## Horário\n\nDas 9h às 19h.", "visibilidade": "publico"}'

# Buscar. Sem "visibilidade", a busca só enxerga documentos públicos.
curl 'localhost:8000/busca?pergunta=horario&k=3'
```

| Rota | O que faz |
|---|---|
| `POST /documentos` | Recebe `nome`, `conteudo` e `visibilidade` (`publico` ou `interno`). Reenviar o mesmo `nome` substitui o documento anterior |
| `GET /busca` | Recebe `pergunta`, `k` (1 a 10, padrão 3) e `visibilidade` (padrão `publico`). Devolve `{"resultados": [{trecho, documento, score}]}` |
| `GET /health` | Diz se o serviço está de pé |

## Como é por dentro

| Arquivo | Papel |
|---|---|
| `dominio.py` | Conceitos (documento, trecho, visibilidade) e as interfaces `Embedder` e `Repositorio` |
| `acervo.py` | Os dois casos de uso: ingerir e buscar |
| `chunking.py` | Divisão do texto em trechos ([ADR 0002](../../docs/adr/0002-chunking.md)) |
| `embeddings.py` | Texto em vetor ([ADR 0003](../../docs/adr/0003-embeddings.md)) |
| `repositorio_memoria.py` | Armazenamento em memória, usado nos testes e quando não há `DATABASE_URL` |
| `repositorio_postgres.py` | Armazenamento em Postgres + pgvector. O filtro de visibilidade está no SQL |
| `config.py` | Lê as variáveis de ambiente e escolhe repositório e embedder |
| `main.py` | Rotas HTTP e validação da entrada |

## Configuração

| Variável | Padrão | Para que serve |
|---|---|---|
| `DATABASE_URL` | vazio (memória) | Endereço do Postgres. No `docker compose` já vem preenchido |
| `EMBEDDINGS_PROVIDER` | `fake` | `fake` (sem chave) ou `openai` (qualquer serviço no formato da OpenAI) |
| `EMBEDDINGS_DIM` | `1024` | Tamanho do vetor. Tem que bater com o modelo. Mudar exige recriar o banco |
| `EMBEDDINGS_BASE_URL`, `EMBEDDINGS_MODEL`, `EMBEDDINGS_API_KEY` | vazio | Só para `openai` |

Configuração inválida impede o serviço de iniciar, com a mensagem do que falta.

## Testes

```bash
pytest services/core-api                 # em memória; os testes de Postgres são pulados
DATABASE_URL_TESTE=postgresql://USUARIO:SENHA@localhost:5432/atende_teste pytest services/core-api
```

O banco de teste é separado do banco de desenvolvimento porque os testes apagam as tabelas. Para criar: `docker compose exec db createdb -U atende atende_teste`. No CI ele já existe.
