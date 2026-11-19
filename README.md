# atende-ai

Plataforma de conhecimento e atendimento com IA para pequenos negócios.

O sistema tem duas metades ligadas por um contrato MCP:

1. **Núcleo de conhecimento:** recebe os documentos do negócio, extrai e indexa o conteúdo e responde buscas (RAG).
2. **Agente de atendimento:** conversa com os clientes pelo WhatsApp, consulta o núcleo pelas ferramentas MCP e executa ações (agenda, cadastro, pagamento).

## Estrutura

```
services/
  core-api/      núcleo: ingestão, extração, RAG
  mcp-server/    ferramentas expostas para agentes
  agent/         agente (no terminal na Etapa 1; WhatsApp na Etapa 3)
exemplos/        documentos de exemplo para ingerir
tests/           testes de integração entre os serviços
pipelines/       orquestração e jobs de dados
ml/              treino, avaliação, modelos
infra/           Docker e configuração de deploy
docs/
  adr/           decisões de arquitetura
  semanal/       resumo semanal (roteiro da apresentação)
```

## Status das etapas

| Etapa | O que entrega | Estado |
|---|---|---|
| 1. Esqueleto de ponta a ponta e contrato MCP | Documento entra, é indexado, e um agente no terminal responde citando a fonte | Implementada, aguardando revisão dos PRs (#10 a #18) |
| 2. Aprofundar o núcleo de conhecimento | PDF e OCR, pipeline de ingestão, busca híbrida, avaliação no CI | Não iniciada |
| 3. Agente no WhatsApp respondendo dúvidas | WhatsApp, histórico de conversa, transferência para humano, LGPD | Não iniciada |
| 4. Ações e documentos pela conversa | Agenda e pagamento por MCP, documentos enviados pelo cliente | Não iniciada |

## Como rodar

Pré-requisitos: Docker (com Docker Compose) e Python 3.12.

```bash
cp .env.example .env                 # funciona sem nenhuma chave de API
docker compose up -d --wait          # sobe banco, core-api e mcp-server

python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"              # instala o agente e as ferramentas de teste

python -m agent.cli ingest exemplos/faq-salao.md --visibilidade publico
python -m agent.cli ask "Qual o horário de funcionamento?"
```

Saída esperada do último comando:

```
Resposta:
  Abrimos de terça a sábado, das 9h às 19h. Fechamos aos domingos, segundas e feriados. [faq-salao.md]

Fontes:
  [1] faq-salao.md (score 0.33)
      ## Horário de funcionamento
      Abrimos de terça a sábado, das 9h às 19h. Fechamos aos domingos, segundas e feriados.
```

Para ver a regra de visibilidade funcionando, envie o documento interno de exemplo e pergunte por algo que só ele tem. O agente responde que não encontrou:

```bash
python -m agent.cli ingest exemplos/custos-internos.md --visibilidade interno
python -m agent.cli ask "Qual a comissão da equipe?"
# Resposta:
#   Não encontrei essa informação no acervo.
```

### Variáveis de ambiente

Todas ficam no `.env` (que nunca vai para o Git). Os padrões do `.env.example` bastam para rodar.

| Variável | Padrão | Para que serve |
|---|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | ver `.env.example` | Banco local. Troque a senha |
| `DB_PORT`, `CORE_API_PORT`, `MCP_SERVER_PORT` | `5432`, `8000`, `8001` | Portas na sua máquina (só em `127.0.0.1`) |
| `EMBEDDINGS_PROVIDER` | `fake` | `fake` (sem chave) ou `openai` (serviço no formato da API da OpenAI) |
| `EMBEDDINGS_DIM` | `1024` | Tamanho do vetor. Mudar exige recriar o banco: `docker compose down -v` |
| `EMBEDDINGS_BASE_URL`, `EMBEDDINGS_MODEL`, `EMBEDDINGS_API_KEY` | vazio | Só para `EMBEDDINGS_PROVIDER=openai` |
| `LLM_PROVIDER` | `fake` | `fake` (sem chave) ou `anthropic` (Claude redige a resposta) |
| `LLM_MODEL`, `ANTHROPIC_API_KEY` | `claude-opus-5-5`, vazio | Só para `LLM_PROVIDER=anthropic` |
| `SCORE_MINIMO` | `0.1` | Trechos com score abaixo disso são ignorados pelo agente. Depende do modelo de embedding |
| `CORE_API_HOSTS` | `localhost,127.0.0.1,core-api` | Valores de `Host` que o core-api aceita |
| `CORE_API_URL`, `MCP_SERVER_URL` | `http://localhost:8000`, `http://localhost:8001/mcp` | Para onde o agente aponta |

### Testes

```bash
ruff check .
pytest                               # tudo em memória; os testes de Postgres são pulados

# Para rodar também contra o Postgres (o CI sempre roda):
docker compose exec db createdb -U atende atende_teste
DATABASE_URL_TESTE=postgresql://atende:SUA_SENHA@localhost:5432/atende_teste pytest
```

## Arquitetura atual

O que existe de fato ao fim da Etapa 1:

```mermaid
flowchart LR
    pessoa([Pessoa no terminal])

    subgraph maquina["Na sua máquina"]
        cli["agent<br/>CLI ingest / ask"]
        llm["LLM<br/>falso (padrão) ou Claude"]
    end

    subgraph docker["docker compose"]
        mcp["mcp-server<br/>buscar_conhecimento(pergunta, k)"]
        core["core-api<br/>POST /documentos · GET /busca"]
        db[("Postgres + pgvector<br/>documentos e trechos")]
    end

    pessoa --> cli
    cli -- "ask: contrato MCP<br/>(só conteúdo público)" --> mcp
    mcp -- "HTTP, sempre com<br/>visibilidade=publico" --> core
    cli -- "ingest: HTTP direto" --> core
    core -- "chunking + embeddings<br/>filtro de visibilidade no SQL" --> db
    cli --> llm
```

Como ler o desenho:

- **Uma pergunta (`ask`)** sai do agente, passa pelo servidor MCP e chega ao core-api. O servidor MCP é a única porta do agente para o acervo, e por ela só passa conteúdo `publico`.
- **Um documento (`ingest`)** vai direto ao core-api. Enviar documento é tarefa de quem administra o acervo, então não existe ferramenta MCP para isso.
- **O core-api** divide o texto em trechos, transforma cada trecho num vetor (embedding) e guarda no Postgres. Na busca, compara o vetor da pergunta com os dos trechos.
- **O LLM** só redige a resposta a partir dos trechos que a busca devolveu. As fontes mostradas vêm da busca, não do texto do modelo.

A regra de visibilidade tem três travas independentes, e há teste para cada uma: a ferramenta MCP não tem parâmetro de visibilidade, o servidor MCP fixa `publico` em toda consulta, e o core-api assume `publico` quando ninguém informa.

Cada serviço tem um README com mais detalhe: [core-api](services/core-api/README.md), [mcp-server](services/mcp-server/README.md) (o contrato), [agent](services/agent/README.md), [infra](infra/README.md), [tests](tests/README.md).

## Registro de mudanças

### Etapa 1: esqueleto de ponta a ponta e contrato MCP (2026-11-18)

**O que foi feito**
- Plataforma: `pyproject.toml`, `docker-compose.yml`, `.env.example` e CI instalando o projeto com Postgres + pgvector (#10).
- Contrato MCP: a ferramenta `buscar_conhecimento(pergunta, k)` documentada (#11).
- Núcleo: `POST /documentos`, chunking, embeddings e `GET /busca` com filtro de visibilidade (#12).
- Núcleo: armazenamento em Postgres + pgvector e embedding real opcional (#13).
- Servidor MCP implementando o contrato sobre o core-api (#14).
- Agente: interface de LLM com versão falsa e Claude (#16).
- Agente: comandos `ingest` e `ask`, respondendo com trecho e documento de origem (#17).
- Integração: teste de ponta a ponta e teste de vazamento de documento interno (#18).

**Decisões**
- Contrato MCP devolve `{"resultados": [...]}` e a ferramenta não tem parâmetro de visibilidade: [ADR 0001](docs/adr/0001-contrato-mcp.md).
- Um trecho por título markdown, com limite de 800 caracteres: [ADR 0002](docs/adr/0002-chunking.md).
- Embeddings atrás de interface, com implementação falsa como padrão e modelo real ainda não escolhido: [ADR 0003](docs/adr/0003-embeddings.md).
- LLM atrás de interface, Claude como modelo real, sem framework de agente nesta etapa: [ADR 0004](docs/adr/0004-llm-do-agente.md).

**Como verificar**
- Os comandos de "Como rodar" acima, num clone limpo.
- `pytest tests/test_ponta_a_ponta.py`: o documento entra e o agente responde citando a fonte.
- `pytest tests/test_vazamento.py`: documento `interno` nunca chega ao agente.
- CI verde em todos os PRs, com os testes rodando também contra o Postgres.
- Revisão independente de segurança e de código feita por agentes sobre a pilha inteira: nenhum caminho de vazamento de conteúdo interno encontrado; os ajustes apontados entraram nos próprios PRs.

**Limitações conhecidas / próximo passo**
- **Sem autenticação** no core-api e no servidor MCP. As portas só abrem em `127.0.0.1`. Tem que ser resolvido antes de qualquer deploy.
- **Com o embedder falso a busca compara palavras, não significado.** "Que horas vocês abrem?" não encontra "Horário de funcionamento": devolve o trecho de cancelamento, por causa da palavra "horas". E uma pergunta fora do acervo às vezes encontra um trecho por coincidência (21% das perguntas aleatórias no FAQ de exemplo). A Etapa 2 escolhe um modelo real com medição.
- Só texto e markdown. PDF, imagem e OCR entram na Etapa 2.
- Chunking de tamanho fixo escolhido sem medição, sem índice aproximado no banco e sem reprocessamento ao trocar de modelo. Tudo isso é da Etapa 2.
- O Claude como LLM foi testado só com um cliente simulado. Falta uma execução com chave real.
- O nome do arquivo é a identidade do documento: reenviar `faq.md` substitui o anterior, inclusive a visibilidade, sem aviso. Dois arquivos com o mesmo nome em pastas diferentes colidem.
- As dependências têm faixa de versão, mas não há arquivo de lock, e as actions do CI estão presas por tag, não por SHA.
- Nenhum teste automático sobe o `docker compose`. Foi verificado à mão.

## Como contribuir

Leia o [CONTRIBUTING.md](CONTRIBUTING.md) antes do primeiro PR. Resumo: ninguém envia direto na `main`, todo trabalho entra por PR pequeno, com CI verde e uma aprovação.

## Equipe

| Área | Dono | Revisor da vez |
|---|---|---|
| Ingestão e pipeline | a definir | a definir |
| Busca e RAG | a definir | a definir |
| ML e extração | a definir | a definir |
| MCP | a definir | a definir |
| Agente | a definir | a definir |
| Plataforma (CI, infra, avaliação) | @neozmmv | a definir |
