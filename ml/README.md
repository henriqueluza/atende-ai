# ml

Avaliação da busca. Treino e modelos próprios ainda não existem.

```bash
python ml/avaliacao/rodar.py                 # em memória; é o que o CI roda
python ml/avaliacao/rodar.py --corte 0.3     # experimenta outro corte do atendente
python ml/avaliacao/rodar.py --banco postgresql://...   # no Postgres (APAGA o acervo desse banco)
```

| Arquivo | Papel |
|---|---|
| `avaliacao/perguntas.jsonl` | Perguntas de cliente e o documento de `exemplos/` que tem a resposta |
| `avaliacao/fora-do-acervo.jsonl` | Perguntas que o acervo público não responde |
| `avaliacao/acervo.json` | Quais exemplos entram e com que visibilidade |
| `avaliacao/minimos.json` | Abaixo disso o CI reprova. Só suba junto com a mudança que melhorou a busca |
| `avaliacao/rodar.py` | Roda os três modos de busca e compara o padrão com os mínimos |

O que cada número significa e por que medimos assim: [ADR 0008](../docs/adr/0008-avaliacao-da-busca.md).

Para medir o acervo de verdade de um negócio, escreva um arquivo no formato de `perguntas.jsonl` e envie com `python -m agent.cli avaliar arquivo.jsonl`. O resultado aparece em "Qualidade da busca" no aplicativo.
