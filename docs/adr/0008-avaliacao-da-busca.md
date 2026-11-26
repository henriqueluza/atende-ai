# ADR 0008: avaliação da busca

- **Data:** 2026-11-23
- **Status:** aceita

## Contexto

Chunking, modelo de embedding e modo de busca foram escolhidos na Etapa 1 sem medição. Sem número, não dá para saber se uma mudança melhorou ou piorou a busca.

## Decisão

Um conjunto fixo de perguntas de cliente, cada uma com o documento que tem a resposta (`ml/avaliacao/perguntas.jsonl`), e um conjunto de perguntas que o acervo não responde (`fora-do-acervo.jsonl`). Para cada modo de busca medimos:

- **acerto:** o documento certo aparece entre os 3 primeiros trechos;
- **MRR:** em que posição ele aparece, em média;
- **recusa fora do acervo** e **respondidas:** o que o corte de score do atendente faz com cada conjunto.

`python ml/avaliacao/rodar.py` roda isso sobre `exemplos/` e reprova se o modo padrão ficar abaixo de `ml/avaliacao/minimos.json`. O CI roda a cada PR, em memória, para o resultado ser sempre o mesmo.

O mesmo cálculo fica disponível no servidor: `POST /avaliacao/execucoes` roda um conjunto contra o acervo de verdade e guarda o resultado; `GET /avaliacao` devolve o histórico, que o aplicativo mostra em "Qualidade da busca".

## Alternativas consideradas

- Avaliar a resposta final com um LLM juiz: mede o que importa para o cliente, mas custa por execução e varia entre execuções. Faz sentido quando o Claude estiver ligado com chave real.
- Marcar o trecho certo, não o documento: mais preciso, mas o gabarito quebra a cada mudança de chunking, que é justamente o que queremos poder testar.

## Consequências

- Mudança que piora a busca no acervo de exemplo não passa no CI. Melhorar de propósito exige subir os mínimos no mesmo PR.
- 30 perguntas sobre um acervo de salão é pouco: uma pergunta vale 3,3 pontos. Serve para pegar regressão, não para comparar modelos parecidos.
- Os mínimos valem para o embedder falso. Com modelo real, é preciso medir e gravar outros.
