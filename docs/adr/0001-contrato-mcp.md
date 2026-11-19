# ADR 0001: formato do contrato MCP e regra de visibilidade

- **Data:** 2026-11-18
- **Status:** proposta

## Contexto

O sistema tem duas metades, o núcleo de conhecimento e o agente, ligadas por ferramentas MCP. Quem escreve o agente e quem escreve o núcleo precisam combinar o formato antes de começar, e mudar esse formato depois obriga a mexer nos dois lados.

Além disso, o acervo tem documentos sigilosos (`interno`) e o agente fala com o público. Precisamos decidir em que ponto do sistema fica a garantia de que o agente nunca recebe conteúdo interno.

## Decisão

1. A Etapa 1 tem uma ferramenta: `buscar_conhecimento(pergunta, k)`, documentada em `services/mcp-server/README.md`.
2. A saída é um objeto `{"resultados": [{trecho, documento, score}]}`, e não uma lista solta.
3. A ferramenta **não tem parâmetro de visibilidade**. O servidor MCP sempre consulta o núcleo pedindo `publico`, e o núcleo, quando ninguém informa a visibilidade, também assume `publico`.
4. O contrato só cresce: campos e ferramentas novos podem entrar, nada existente muda de nome, tipo ou significado.
5. Nomes das ferramentas e dos campos em português, como o resto do domínio.

## Alternativas consideradas

- **Devolver uma lista solta**, como no plano original: o MCP exige que a saída estruturada seja um objeto, então o SDK embrulharia a lista num campo genérico `result`. Com um objeto nosso, o nome do campo é escolhido por nós e dá para acrescentar informação depois (por exemplo, um aviso de "não há resposta confiável", previsto para a Etapa 3) sem quebrar ninguém.
- **Parâmetro `visibilidade` na ferramenta, com padrão `publico`**: bastaria uma mensagem maliciosa convencer o modelo a passar `interno` para vazar documento sigiloso. Deixar a escolha fora do alcance do agente elimina essa classe de erro.
- **Filtrar só no agente**: o conteúdo interno já teria saído do núcleo. O filtro tem que ficar o mais perto possível do dado.
- **Uma ferramenta por tipo de pergunta** (preço, horário, política): amarra o contrato a um tipo de negócio. A busca genérica serve para qualquer acervo.

## Consequências

- Fica mais fácil: núcleo, servidor MCP e agente podem ser feitos em paralelo; o teste de vazamento tem um ponto claro para verificar.
- Fica mais difícil: quando a equipe interna precisar consultar documentos `interno` (previsto na visão do projeto), isso não passa por esta ferramenta. Vai exigir outro caminho, com autenticação, e outro ADR.
- A revisar depois: autenticação entre agente, servidor MCP e núcleo (hoje não há, e as portas só abrem em `127.0.0.1`); limite de requisições por cliente.
