# agent

Agente de atendimento: um cliente MCP que busca trechos no acervo público e pede a um LLM a resposta, sempre citando a fonte. Roda no terminal e como serviço HTTP (é o que o aplicativo de desktop usa). O WhatsApp entra na Etapa 3.

## Como usar

Com o sistema no ar (`docker compose up -d`) e o projeto instalado (`pip install -e ".[dev]"`), na raiz do repositório:

```bash
# Enviar um documento ao acervo. A visibilidade é obrigatória.
python -m agent.cli ingest exemplos/faq-salao.md --visibilidade publico

# Perguntar. A resposta vem com o trecho e o nome do documento usado como fonte.
python -m agent.cli ask "Qual o horário de funcionamento?"

# PDF e imagem entram na fila do core-api e aparecem na busca em alguns segundos.
python -m agent.cli ingest tabela-de-precos.pdf --visibilidade publico

# Medir a busca com um conjunto de perguntas. O resultado aparece no aplicativo.
python -m agent.cli avaliar ml/avaliacao/perguntas.jsonl --versao "$(git rev-parse --short HEAD)"

# O mesmo atendente por HTTP (no docker compose ele já sobe, na porta 8002).
curl -X POST localhost:8002/perguntas -H 'content-type: application/json' \
  -d '{"pergunta": "Qual o horário de funcionamento?"}'
# {"texto": "...", "fontes": [{"trecho", "documento", "score"}], "respondeu": true}
```

Por padrão não precisa de chave: o LLM falso responde com o trecho mais parecido. Para o Claude redigir a resposta, coloque no `.env`:

```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sua-chave
```

| Variável | Padrão | Para que serve |
|---|---|---|
| `LLM_PROVIDER` | `fake` | `fake` (sem chave) ou `anthropic` |
| `LLM_MODEL` | `claude-opus-5-5` | Modelo do Claude, quando `LLM_PROVIDER=anthropic` |
| `SCORE_MINIMO` | `0.2` | Trechos com score abaixo disso são ignorados. Medido com a busca híbrida ([ADR 0007](../../docs/adr/0007-busca-hibrida.md)): reajuste ao trocar de modelo |
| `AGENT_HOSTS` | `localhost,127.0.0.1,agent` | Valores de `Host` que o serviço HTTP aceita |
| `MCP_SERVER_URL` | `http://localhost:8001/mcp` | Onde está o servidor MCP |
| `CORE_API_URL` | `http://localhost:8000` | Onde está o core-api (só o `ingest` usa) |

## Como é por dentro

| Arquivo | Papel |
|---|---|
| `atendente.py` | O fluxo do agente: buscar pelo MCP e pedir a resposta ao LLM |
| `llm.py` | Interface `LLM`, o `LLMFalso` e o `LLMClaude` ([ADR 0004](../../docs/adr/0004-llm-do-agente.md)) |
| `cli.py` | Comandos `ingest`, `ask` e `avaliar` |
| `servico.py` | O atendente por HTTP: `POST /perguntas` e `GET /health` |

Dois caminhos diferentes, de propósito:

- **`ask` passa pelo servidor MCP**, como qualquer agente. Por ali só existe conteúdo público.
- **`ingest` fala direto com o core-api.** Enviar documento é tarefa de quem administra o acervo, não do agente que conversa com o público, então não existe ferramenta MCP para isso.

O CLI lê do `.env` só as variáveis desta tabela e `ANTHROPIC_API_KEY`.

Testes: `pytest services/agent` (servidor MCP simulado, sem rede).
