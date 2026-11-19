# ADR 0003: embeddings atrás de uma interface, com implementação falsa como padrão

- **Data:** 2026-11-18
- **Status:** proposta

## Contexto

Para buscar por significado, cada trecho vira um vetor de números (embedding), e a busca compara o vetor da pergunta com os vetores dos trechos. Gerar embeddings de boa qualidade exige um modelo, que normalmente é um serviço pago e pede chave de API.

Dois princípios do projeto pesam aqui: os testes rodam sem chave de API, e qualquer pessoa sobe o sistema num clone limpo com um comando.

## Decisão

1. O núcleo depende só de uma interface pequena, `Embedder`, com um método `gerar(textos)` e um atributo `dimensao`.
2. O padrão é o `EmbedderFalso`: determinístico, sem rede, de 1024 dimensões. Cada palavra soma 1 numa posição do vetor escolhida pelo hash da palavra, então textos com palavras em comum ficam próximos. Medimos com 2.000 perguntas de palavras aleatórias contra o FAQ de exemplo: com 256 dimensões, 61% encontravam algum trecho por coincidência (palavras diferentes caindo na mesma posição); com 1024, 21%; com 4096, 6%. Ficamos em 1024 como meio-termo entre coincidências e tamanho no banco.
3. O embedding real é opcional e ligado por variável de ambiente (`EMBEDDINGS_PROVIDER=openai`), falando com qualquer serviço que siga o formato da API de embeddings da OpenAI (OpenAI, Voyage, Ollama local e outros). O modelo é configurado por variável, não fixado no código. Essa parte entra no PR do Postgres (#5).
4. A dimensão do vetor é configuração (`EMBEDDINGS_DIM`) e define a coluna do banco. Trocar de modelo exige reindexar o acervo.

## Alternativas consideradas

- **Fixar um modelo agora** (por exemplo, `text-embedding-3-small`): a escolha deveria ser feita com medição, e o conjunto de avaliação só existe na Etapa 2. Fixar agora seria chute.
- **Modelo local com `sentence-transformers`**: funciona sem chave, mas acrescenta gigabytes à imagem Docker e minutos ao CI.
- **Simular a chamada só nos testes** (mock): o sistema não rodaria num clone limpo sem chave, e o teste de ponta a ponta não exercitaria o caminho real.

## Consequências

- Fica mais fácil: CI rápido e gratuito; o critério de pronto da etapa funciona sem cadastro em serviço nenhum; trocar de fornecedor é mexer no `.env`.
- Fica mais difícil: com o embedder falso a busca só acerta quando a pergunta usa as mesmas palavras do documento. "Que horas vocês abrem?" não encontra "Horário de funcionamento". Quem for demonstrar precisa saber disso.
- A revisar na Etapa 2: escolher o modelo real com base na avaliação e registrar em ADR novo; definir o reprocessamento do acervo quando o modelo mudar.
