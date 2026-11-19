# ADR 0004: LLM do agente atrás de uma interface, sem framework de agente na Etapa 1

- **Data:** 2026-11-18
- **Status:** proposta

## Contexto

O agente recebe uma pergunta, busca trechos no acervo pelo servidor MCP e precisa transformar esses trechos numa resposta que cite a fonte. Quem redige a resposta é um modelo de linguagem (LLM), que é um serviço pago e pede chave de API. Os testes e o clone limpo têm que funcionar sem chave.

O plano do projeto deixa em aberto qual framework de agente usar.

## Decisão

1. O agente depende de uma interface de um método: `LLM.responder(pergunta, fontes)`.
2. O padrão é o `LLMFalso`: devolve o trecho mais parecido com o nome do documento. Determinístico e gratuito.
3. O LLM real é o Claude, pelo SDK oficial da Anthropic, ligado por `LLM_PROVIDER=anthropic`. O modelo padrão é `claude-opus-5-5`, trocável por `LLM_MODEL`.
4. **Sem framework de agente nesta etapa.** O fluxo é fixo e escrito em código: buscar (sempre) e depois redigir. O modelo não decide se busca nem qual ferramenta chama.
5. As fontes mostradas ao usuário vêm da busca, e não do texto do modelo. Mesmo que o modelo erre a citação, a lista de fontes está certa.
6. Se nenhum trecho passa de um score mínimo (0,1), o agente responde "Não encontrei essa informação no acervo." sem chamar o modelo.
7. Os trechos entram no prompt dentro de marcações, com `<`, `>` e aspas trocados, e as instruções dizem para tratá-los como material de consulta.

## Alternativas consideradas

- **Framework agora** (LangGraph, PydanticAI, Agent SDK): a Etapa 1 tem um passo de busca e um de redação. O framework traria conceitos para explicar na apresentação sem resolver problema que exista hoje. A decisão fica para a Etapa 3, quando houver histórico de conversa e transferência para humano.
- **Deixar o modelo decidir quando chamar a ferramenta** (tool use): é o desenho natural das Etapas 3 e 4, com várias ferramentas. Com uma ferramenta só, buscar sempre é mais previsível e mais fácil de testar.
- **Modelo menor por padrão**: decisão de custo que cabe ao grupo. Basta mudar `LLM_MODEL` no `.env`.

## Consequências

- Fica mais fácil: teste de ponta a ponta sem chave; trocar de modelo sem mexer em código; explicar o fluxo em duas frases.
- Fica mais difícil: o `LLMFalso` não redige, só repete o trecho. A qualidade da resposta com o Claude não é medida por nenhum teste automático ainda.
- Risco conhecido: um documento público malicioso ainda pode tentar manipular o modelo (prompt injection). As marcações e as instruções reduzem o risco, mas não eliminam. O que protege o conteúdo interno não é o prompt, e sim o fato de o agente não ter como pedi-lo (ADR 0001).
- A revisar na Etapa 3: framework de agente, tool use, guardrails de saída e avaliação das respostas.
