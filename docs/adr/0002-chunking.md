# ADR 0002: como dividir os documentos em trechos (chunking)

- **Data:** 2026-11-18
- **Status:** proposta

## Contexto

A busca não devolve o documento inteiro, e sim pedaços dele ("trechos"). O tamanho e o ponto de corte dos trechos mudam o que o agente recebe: trecho grande demais mistura assuntos, trecho pequeno demais perde o contexto. Na Etapa 1 só entram texto e markdown, e o objetivo é ter o fluxo inteiro funcionando, não a melhor busca.

## Decisão

Um trecho novo começa a cada título markdown (linha que começa com `#`) ou quando o trecho passaria de **800 caracteres**. Parágrafos não são cortados no meio, exceto quando um parágrafo sozinho passa do limite. Não há sobreposição entre trechos.

O código está em `services/core-api/core_api/chunking.py`.

## Alternativas consideradas

- **Tamanho fixo com sobreposição** (por exemplo, 500 caracteres com 50 repetidos): corta frases e respostas no meio. Num FAQ, a pergunta ficaria num trecho e a resposta em outro.
- **Contar tokens em vez de caracteres**: exige a biblioteca do modelo de embedding, que ainda não foi escolhido. Caracteres bastam para um limite aproximado.
- **Biblioteca pronta** (LangChain, LlamaIndex): dependência grande para umas 30 linhas de código. Reavaliar na Etapa 2 se o pipeline de ingestão pedir.

## Consequências

- Fica mais fácil: documentos no formato pergunta e resposta, com um título por assunto, viram um trecho por assunto, que é o caso do exemplo da etapa.
- Fica mais difícil: texto corrido sem títulos é cortado só por tamanho, e uma resposta que atravessa dois trechos pode não ser encontrada inteira.
- A revisar na Etapa 2: o tamanho de 800 foi escolhido sem medição. Quando existir o conjunto de perguntas de avaliação, testar outros tamanhos e sobreposição com número na mão.
