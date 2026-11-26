# ADR 0007: busca híbrida

- **Data:** 2026-11-23
- **Status:** aceita

## Contexto

A busca só por embedding erra quando a pergunta depende de uma palavra exata ("buço", "progressiva", um nome). E o cliente escreve sem acento.

## Decisão

`GET /busca` aceita `modo`: `semantica`, `palavras` ou `hibrida`. O padrão do servidor passa a ser `hibrida` (`BUSCA_MODO`).

- **Nota por palavras (cobertura):** a fração das palavras da pergunta que aparecem no trecho, de 0 a 1. No Postgres as palavras passam pelo dicionário de português (radical e palavras vazias), sobre o texto em minúsculas e sem acento, com índice GIN.
- **Nota híbrida:** `peso × semelhança do embedding + (1 − peso) × cobertura`, com `peso = 0,5` (`BUSCA_PESO_SEMANTICO`).
- **Candidatos:** os mais próximos pelo vetor (agora com índice HNSW) unidos aos que têm alguma palavra da pergunta. As duas notas são calculadas de forma exata para cada candidato. O filtro de visibilidade está em cada parte da consulta.

Medido com `python ml/avaliacao/rodar.py` (30 perguntas, embedder falso, k=3):

| Modo | Acerto | MRR |
|---|---|---|
| semântica | 90,0% | 0,88 |
| palavras | 96,7% | 0,94 |
| híbrida | 96,7% | 0,93 |

Com a híbrida, o corte do atendente (`SCORE_MINIMO`) subiu de 0,1 para 0,2: recusa 70% das perguntas fora do acervo e mantém 90% das que têm resposta. Com 0,1 recusava só 40%.

## Alternativas consideradas

- Fusão por posição (RRF): é o mais usado, mas a nota resultante não diz se o trecho é relevante, e o atendente depende de um corte para responder "não encontrei".
- BM25 (extensão ou serviço à parte): melhor em acervo grande; aqui são dezenas de documentos.

## Consequências

- **A medição foi feita com o embedder falso, que já compara palavras.** Ela mostra que a parte por palavras ajuda, mas não diz quanto ela soma a um modelo real. Ao escolher o modelo, rode de novo e reajuste peso e corte.
- Com o embedder falso, "Que horas vocês abrem?" ainda traz primeiro o trecho de remarcação, por causa de "4 horas". O trecho certo vem entre os três primeiros.
- Palavra vazia escrita sem acento ("voces", "nao") não é descartada pelo dicionário e baixa um pouco a cobertura.
- O repositório em memória usa uma aproximação mais simples do dicionário. Os números dele e do Postgres diferem um pouco.
