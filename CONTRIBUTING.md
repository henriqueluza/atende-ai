# Como contribuir

## Regras

- **`main` protegida:** ninguém envia direto. Tudo entra por pull request.
- **Uma branch por issue**, com vida curta (dois ou três dias).
- **PR pequeno:** mire em até ~200 linhas. PR grande demais deve ser dividido.
- **Para fazer merge:** CI verde e uma aprovação de outra pessoa.
- **Merge por squash**, para a `main` ter um commit por PR.

## Passo a passo

1. Pegue uma issue no quadro do projeto e coloque seu nome nela.
2. Crie a branch a partir da `main` atualizada:
   ```bash
   git switch main && git pull
   git switch -c feat/12-busca-hibrida
   ```
3. Faça commits pequenos e envie a branch.
4. Abra o PR preenchendo o template. Escreva a descrição para um colega de outra área entender.
5. Responda à revisão, espere a aprovação e faça o merge.

## Nomes de branch

`tipo/numero-da-issue-descricao-curta`

| Tipo | Uso |
|---|---|
| `feat` | funcionalidade nova |
| `fix` | correção de bug |
| `docs` | documentação |
| `chore` | configuração, CI, dependências |
| `refactor` | mudança interna sem alterar comportamento |

## Mensagens de commit

Seguimos o [Conventional Commits](https://www.conventionalcommits.org/pt-br/): `tipo(área): o que mudou`.

```
feat(core-api): adiciona endpoint de ingestão de PDF
fix(agent): corrige perda de histórico da conversa
```

## Revisão

- O revisor muda em rodízio, para todo mundo conhecer todas as áreas.
- Revise em até 24 horas. PR parado trava o colega.
- Revisão por agente de IA é a primeira passada. A aprovação é sempre de uma pessoa.

## Decisões de arquitetura

Decisão importante ("por que pgvector e não Qdrant") vira um ADR curto em `docs/adr/`, a partir do `0000-template.md`.

## Resumo semanal

Toda semana cada dono de área escreve três ou quatro linhas em `docs/semanal/`, a partir do `TEMPLATE.md`. Esse arquivo é o roteiro da apresentação, seja quem for o sorteado.
