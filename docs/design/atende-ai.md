# Design system do atende-ai (aplicativo de desktop)

Fonte da verdade para a interface em `apps/desktop`. Os valores vivem em `apps/desktop/src/styles/tokens.css`; mude lá e aqui juntos.

## Direção

**Moldura tingida, folha branca.** A lateral e a barra do topo formam um "L" num cinza levemente verde-azulado, sem linha entre elas. O trabalho acontece numa folha branca com borda de 1px e cantos de 16px, afastada 8px da direita e de baixo. Nada tem sombra em repouso: só o que flutua (menu, diálogo, aviso).

**A cor fica nos dados, não na moldura.** O verde-azulado cheio (`--accent`) aparece na nota de um trecho, na linha do gráfico, no balão do cliente e no ícone da tela ativa. O botão principal é quase preto. Verde e vermelho só para situação (pronto, falhou, subiu, caiu).

**O que só este produto tem**
- A conversa de teste: a resposta como o cliente a receberia, ao lado dos trechos que a sustentam.
- A divisão público/interno em toda parte: "O atendente usa" contra "Só a equipe vê".
- O corte do atendente (0,20) mostrado na pesquisa: trecho abaixo dele aparece apagado, com a frase que explica.

**Palavras.** Português do Brasil, frase em caixa normal, do ponto de vista do dono do negócio: "Quem vê", "O atendente usa", "Pronto", "Falhou". Termos internos (chunk, embedding, MCP) só aparecem em Configurações. Erro diz o que houve e o que fazer; não pede desculpa.

Diais: variância de layout baixa (é ferramenta de trabalho), motion baixa (só resposta a ação), densidade média.

## Tokens

| Papel | Token | Valor |
|---|---|---|
| Moldura | `--ground` | `#f2f5f5` |
| Folha e painéis | `--surface` | `#ffffff` |
| Poço, hover | `--raised` | `#f4f6f7` |
| Item ativo da lateral | `--active` | `#e6eaeb` |
| Borda de painel | `--border` | `#e4e8e9` |
| Linha entre linhas | `--rule` | `#eef1f1` |
| Borda de controle | `--control` | `#c9cdd0` |
| Texto | `--text` | `#131416` |
| Texto secundário | `--muted` | `#55595b` (7:1 no branco) |
| Marcador de lugar | `--faint` | `#63686a` (5,6:1) |
| Cor dos dados | `--accent` | `#1b6c80` |
| Destaque de palavra | `--accent-tint` | `#e3f0f3` |
| Botão principal | `--primary` | `#1d1f20` |
| Bom / ruim / atenção | `--positive` `--negative` `--warning` | `#1e7b4f` `#c4242a` `#92400e` |

Pílulas: tinta escura sobre fundo claro do mesmo tom (`--pill-*-bg`, `--pill-*-ink`). Uma marca de situação por linha.

**Tipografia.** IBM Plex Sans 400/500/600, embutida no app (sem rede). IBM Plex Mono só para identificadores (versão, id). Tamanhos: título 22, seção 16, número de destaque 28 (34 na Qualidade), corpo 14, apoio 13, meta 12. Números sempre com `tabular-nums`, alinhados à direita em coluna.

**Medidas.** Lateral 228px, barra 48px, respiro da folha 24px, um só espaçamento entre blocos (24px), controle 32px (40 em formulário), linha de tabela a partir de 48px. Raios: folha 16, painel 8, controle 6, pílula total.

**Motion.** `--ease-out: cubic-bezier(0.22, 1, 0.36, 1)`; pressionar 120ms, hover 150ms, abrir 200ms. Só `transform` e `opacity`. Nada entra animado ao carregar: movimento é resposta (botão pressionado, menu e diálogo abrindo, mensagem chegando). `prefers-reduced-motion` zera tudo.

## Regras

- Todo bloco tem os quatro estados: carregando (barra cinza do tamanho do valor, sem brilho), vazio (moldura tracejada, uma frase, a próxima ação), erro (dentro do bloco, com "Tentar de novo") e "o servidor ainda não oferece" (função prevista, com atalho para os dados de exemplo).
- Zero é impresso como zero; valor que não existe é um traço cinza.
- Totais e contagens saem das linhas mostradas, nunca são digitados à parte.
- Foco sempre visível (contorno de 2px na cor dos dados). Tudo funciona pelo teclado. Contraste mínimo de 4,5:1 em qualquer texto.
- Abaixo de 900px a moldura some: a lateral vira um menu de tela cheia e a folha ocupa a janela. Abaixo de 640px a tabela de documentos passa as colunas secundárias para a segunda linha.
- Evitar: degradê, brilho, vidro, ícone em quadrado colorido, cartão dentro de cartão, cor na moldura, rótulo em maiúsculas espaçadas.

## Origem

Estilo "framed sheet" do `design-taste-frontend` (semente 1251642894), com a moldura tingida a partir da cor do produto. Conferido com `inspect.mjs --app` em 1440, 768 e 390px: 0 falhas em todas as telas.
