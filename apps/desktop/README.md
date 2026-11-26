# desktop

Aplicativo de desktop do atende-ai, para quem administra o acervo: enviar documentos, pesquisar, testar o atendente e acompanhar a qualidade da busca. Electron + React + TypeScript.

## Como rodar

Pré-requisitos: Node 22 ou mais novo. Para usar dados de verdade, o sistema no ar (`docker compose up -d --wait` na raiz).

```bash
cd apps/desktop
npm ci
npm run dev        # abre a janela com recarga automática
npm start          # compila e abre como o app final
npm run dev:web    # só a tela, no navegador, com dados de exemplo
```

Sem o servidor no ar, a lista mostra o erro com o botão **Ver com dados de exemplo**: um acervo fictício de salão, guardado só na memória.

```bash
npm run typecheck && npm test && npm run build
```

## Telas

| Tela | O que faz |
|---|---|
| Documentos | Lista o acervo com a situação de cada arquivo, envia (botão ou arrastando para a janela), troca a visibilidade e exclui. Atualiza sozinha enquanto houver arquivo na fila |
| Documento | Trechos indexados, com a página, e as etapas do processamento |
| Pesquisa | Trechos que o acervo devolve, com a nota e o corte do atendente. Público ou interno; híbrida, por significado ou por palavras |
| Testar atendente | A resposta que o cliente receberia, com as fontes ao lado. Só conteúdo público |
| Qualidade da busca | Acerto por execução e perguntas que falharam. "Avaliar de novo" repete o último conjunto |
| Configurações | Endereço dos três serviços e dados de exemplo |

Com **dados de exemplo** ligado (Configurações), nada é lido nem gravado no servidor. Se o servidor em uso for de uma versão anterior e não tiver alguma função, a tela diz isso em vez de mostrar dado inventado.

## Como é por dentro

```
electron/main.mjs      janela, permissões, IPC
electron/backend.mjs   único ponto que fala com a rede; valida toda entrada
electron/preload.cjs   ponte: expõe três funções à tela
src/api/tipos.ts       contrato entre tela e servidor
src/api/real.ts        servidor de verdade, via IPC
src/api/exemplo.ts     servidor de exemplo em memória
src/screens/           uma tela por arquivo
src/styles/            tokens e CSS (ver docs/design/atende-ai.md)
```

### O que o aplicativo chama

| Serviço | Chamadas |
|---|---|
| core-api (`8000`) | `GET/POST /documentos`, `POST /documentos/arquivo`, `GET/PATCH/DELETE /documentos/{id}`, `GET /busca`, `GET /avaliacao`, `POST /avaliacao/execucoes` |
| agent (`8002`) | `POST /perguntas` |
| os três | `GET /health` |

O formato de cada resposta está em `src/api/tipos.ts`.

## Segurança

- A tela roda em sandbox, sem Node, com isolamento de contexto. Ela não acessa a rede (`connect-src 'none'`): pede ao processo principal por IPC.
- O processo principal confere a origem de cada chamada, aceita só uma lista fixa de operações e valida todos os campos antes de montar a requisição.
- Endereço de servidor: só `http(s)`, sem usuário e senha. HTTP sem TLS só para `localhost`, porque os serviços ainda não têm autenticação.
- A janela não navega para fora, não abre outras janelas e nega todas as permissões de navegador.
- Dependências com versão exata e `package-lock.json`.

## Limitações conhecidas

- Não há instalador: roda a partir do código. Empacotar (electron-builder ou Forge) e assinar ficam para depois.
- O conjunto de perguntas da avaliação é enviado pela linha de comando; o aplicativo só repete o último.
- Sem autenticação, como o resto do sistema.
- A conversa de teste não guarda histórico entre aberturas do app.
