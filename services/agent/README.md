# agent

Agente de atendimento. Na Etapa 1 ele vive no terminal: é um cliente MCP que busca trechos no acervo público e pede a um LLM a resposta, sempre citando a fonte. O WhatsApp entra na Etapa 3.

## Como usar

Com o sistema no ar (`docker compose up -d`) e o projeto instalado (`pip install -e ".[dev]"`), na raiz do repositório:

```bash
# Enviar um documento ao acervo. A visibilidade é obrigatória.
python -m agent.cli ingest exemplos/faq-salao.md --visibilidade publico

# Perguntar. A resposta vem com o trecho e o nome do documento usado como fonte.
python -m agent.cli ask "Qual o horário de funcionamento?"
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
| `SCORE_MINIMO` | `0.1` | Trechos com score abaixo disso são ignorados. Depende do modelo de embedding: reajuste ao trocar |
| `MCP_SERVER_URL` | `http://localhost:8001/mcp` | Onde está o servidor MCP |
| `CORE_API_URL` | `http://localhost:8000` | Onde está o core-api (só o `ingest` usa) |

## Como é por dentro

| Arquivo | Papel |
|---|---|
| `atendente.py` | O fluxo do agente: buscar pelo MCP e pedir a resposta ao LLM |
| `llm.py` | Interface `LLM`, o `LLMFalso` e o `LLMClaude` ([ADR 0004](../../docs/adr/0004-llm-do-agente.md)) |
| `cli.py` | Comandos `ingest` e `ask` |

Dois caminhos diferentes, de propósito:

- **`ask` passa pelo servidor MCP**, como qualquer agente. Por ali só existe conteúdo público.
- **`ingest` fala direto com o core-api.** Enviar documento é tarefa de quem administra o acervo, não do agente que conversa com o público, então não existe ferramenta MCP para isso.

O CLI lê do `.env` só as variáveis desta tabela e `ANTHROPIC_API_KEY`.

Testes: `pytest services/agent` (servidor MCP simulado, sem rede).
