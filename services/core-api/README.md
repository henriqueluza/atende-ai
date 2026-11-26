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
| `POST /documentos` | Texto ou markdown: recebe `nome`, `conteudo` e `visibilidade` e indexa na hora. Reenviar o mesmo `nome` substitui o anterior |
| `POST /documentos/arquivo?nome=&visibilidade=` | PDF, PNG, JPG ou WEBP no corpo (até 20 MB). Responde 202 com `situacao: na_fila` |
| `GET /documentos` | Todos os documentos, públicos e internos, com trechos, situação, andamento e erro |
| `GET /documentos/{id}` | `{documento, trechos, passos}`: os trechos com a página e as etapas do processamento |
| `PATCH /documentos/{id}` | Troca a `visibilidade` |
| `DELETE /documentos/{id}` | Apaga o documento e seus trechos |
| `GET /busca` | `pergunta`, `k` (1 a 10, padrão 3), `visibilidade` (padrão `publico`) e `modo` (`hibrida`, `semantica` ou `palavras`; padrão do servidor). Devolve `{"resultados": [{trecho, documento, score}]}` |
| `POST /avaliacao/execucoes` | Roda um conjunto de perguntas contra o acervo público e guarda. Sem `perguntas`, repete o último conjunto |
| `GET /avaliacao` | Histórico das execuções e o detalhe da última |
| `GET /health` | Diz se o serviço está de pé |

Só a busca é alcançada pelo atendente (via servidor MCP, sempre com `visibilidade=publico`). O resto é para quem administra o acervo.

```bash
# Enviar um PDF. Ele entra na fila e aparece na busca quando a situação virar "indexado".
curl -X POST 'localhost:8000/documentos/arquivo?nome=precos.pdf&visibilidade=publico' \
  -H 'content-type: application/pdf' --data-binary @precos.pdf
```

## Como é por dentro

| Arquivo | Papel |
|---|---|
| `dominio.py` | Conceitos (documento, trecho, visibilidade) e as interfaces `Embedder` e `Repositorio` |
| `acervo.py` | Casos de uso: ingerir texto, receber arquivo, processar a fila, buscar |
| `extracao.py` | Texto de PDF e imagem, página por página, com as conferências do arquivo ([ADR 0005](../../docs/adr/0005-extracao-de-pdf-e-ocr.md)) |
| `ocr.py` | Leitura de imagem: Tesseract, indisponível e a versão falsa dos testes |
| `fila.py` | A thread que processa os arquivos enviados ([ADR 0006](../../docs/adr/0006-fila-de-ingestao.md)) |
| `avaliacao.py` | Cálculo de acerto e MRR ([ADR 0008](../../docs/adr/0008-avaliacao-da-busca.md)) |
| `palavras.py` | Busca por palavras do repositório em memória |
| `chunking.py` | Divisão do texto em trechos ([ADR 0002](../../docs/adr/0002-chunking.md)) |
| `embeddings.py` | Texto em vetor ([ADR 0003](../../docs/adr/0003-embeddings.md)) |
| `repositorio_memoria.py` | Armazenamento em memória, usado nos testes e quando não há `DATABASE_URL` |
| `repositorio_postgres.py` | Armazenamento em Postgres + pgvector, a consulta híbrida ([ADR 0007](../../docs/adr/0007-busca-hibrida.md)) e a fila. O filtro de visibilidade está no SQL |
| `config.py` | Lê as variáveis de ambiente e escolhe repositório e embedder |
| `main.py` | Rotas HTTP e validação da entrada |

## Configuração

| Variável | Padrão | Para que serve |
|---|---|---|
| `DATABASE_URL` | vazio (memória) | Endereço do Postgres. No `docker compose` já vem preenchido |
| `CORE_API_HOSTS` | `localhost,127.0.0.1,core-api` | Valores de `Host` aceitos. Requisição com outro `Host` recebe 400 |
| `OCR_PROVIDER` | `auto` | `auto` (usa o Tesseract se houver), `tesseract` (exige) ou `nenhum`. No `docker compose` vem `tesseract` |
| `OCR_IDIOMA` | `por` | Idioma do Tesseract |
| `BUSCA_MODO` | `hibrida` | Modo usado quando a requisição não informa `modo` |
| `BUSCA_PESO_SEMANTICO` | `0.5` | Na híbrida, quanto vale o embedding (0 a 1) |
| `FILA` | ligada | `desligada` impede a thread de processamento de iniciar |
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
