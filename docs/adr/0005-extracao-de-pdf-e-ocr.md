# ADR 0005: extração de PDF e OCR

- **Data:** 2026-11-23
- **Status:** aceita

## Contexto

O acervo só aceitava texto e markdown. Negócio pequeno guarda tabela de preços em PDF e tira foto do quadro de serviços.

## Decisão

PDF é lido com `pypdfium2`. Página que já tem texto usa esse texto; página com menos de 20 caracteres é tratada como foto, vira imagem a 144 dpi e passa pelo Tesseract em português. Imagem (PNG, JPG, WEBP) vai direto ao Tesseract. O OCR fica atrás da interface `Ocr`, com uma versão falsa para os testes, como já é com embeddings e LLM.

O arquivo é tratado como não confiável: o tipo é conferido pelos primeiros bytes e não pelo nome, com limite de 20 MB, 200 páginas, 40 milhões de pixels por imagem e 60 segundos de OCR por página.

## Alternativas consideradas

- PyMuPDF: mais rápido e completo, mas a licença AGPL obrigaria a abrir o código do produto.
- pypdf: Python puro, mas não desenha a página, e sem isso não há OCR de PDF escaneado.
- OCR por API (visão de um LLM ou serviço de nuvem): lê melhor foto torta e letra de mão, mas custa por página e manda documento interno para fora. Fica para medir depois, atrás da mesma interface.

## Consequências

- A imagem Docker ganha o Tesseract (cerca de 60 MB). Fora do Docker, sem Tesseract instalado, PDF com texto continua funcionando e imagem falha com uma frase que explica.
- Tabela em PDF vira texto corrido: a relação entre colunas pode se perder.
- O PDFium roda no processo do core-api. Um PDF feito para explorar falha dele atingiria o serviço. Hoje o que protege é o container sem root e a API só em `127.0.0.1`; isolar a leitura em outro processo é o próximo passo antes de expor o sistema.
- Não medimos a qualidade do OCR em foto de celular. Verificado só com texto impresso gerado em teste.
