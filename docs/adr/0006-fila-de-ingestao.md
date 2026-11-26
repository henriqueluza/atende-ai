# ADR 0006: fila de ingestão

- **Data:** 2026-11-23
- **Status:** aceita

## Contexto

Ler um PDF escaneado de 30 páginas leva minutos. A requisição de envio não pode ficar esperando, e quem envia precisa ver o andamento e o motivo quando falha.

## Decisão

`POST /documentos/arquivo` confere o arquivo, guarda no banco e responde na hora com a situação `na_fila`. Uma thread dentro do core-api (`fila.py`) pega o mais antigo, lê, divide, gera os embeddings e marca `indexado` ou `falhou`. A fila é a própria tabela `documentos` (coluna `situacao`), e o arquivo original fica na tabela `arquivos` só enquanto espera. O documento só aparece na busca depois de `indexado`.

Texto e markdown continuam indexados na hora por `POST /documentos`, como na Etapa 1.

## Alternativas consideradas

- Celery ou RQ com Redis: mais um serviço para subir e vigiar, para um volume de dezenas de documentos por negócio.
- Serviço separado em `pipelines/`: mesma lógica com mais um container. A consulta que pega o próximo já usa `FOR UPDATE SKIP LOCKED`, então separar depois não exige mudar o banco.
- Processar dentro da requisição: simples, mas trava em arquivo grande e perde tudo se a conexão cair.

## Consequências

- Nenhum serviço novo. Se o core-api cair no meio, o documento volta para a fila quando ele subir.
- Um arquivo ruim vira `falhou` com uma frase para quem enviou e não para a fila.
- Um arquivo por vez. Com `uvicorn --workers N` seriam N por vez.
- Falha não é tentada de novo sozinha: é preciso reenviar. E o arquivo original é apagado depois de indexado, então trocar de modelo de embedding ainda exige reenviar os documentos.
