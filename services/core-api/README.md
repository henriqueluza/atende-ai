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
| `repositorio_memoria.py` | Armazenamento em memória, usado nos testes |
| `main.py` | Rotas HTTP e validação da entrada |

Testes: `pytest services/core-api`.
