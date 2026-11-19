# tests

Testes de integração: ligam o core-api, o servidor MCP e o agente de verdade, dentro do processo de teste. Não usam Docker nem chave de API. Os testes de cada serviço isolado ficam em `services/<serviço>/tests`.

| Arquivo | O que prova |
|---|---|
| `test_ponta_a_ponta.py` | Um documento entra, é indexado, e o agente responde citando o trecho e o documento |
| `test_vazamento.py` | Documento `interno` nunca chega ao agente, nem com pergunta feita para burlar a regra |
| `conftest.py` | Monta o sistema inteiro em memória. Cada teste roda duas vezes: acervo em memória e no Postgres |

```bash
pytest tests                    # só em memória (os de Postgres são pulados)
DATABASE_URL_TESTE=postgresql://USUARIO:SENHA@localhost:5432/atende_teste pytest tests
```

No CI os dois modos rodam sempre.

**Se o `test_vazamento.py` falhar, não ajuste o teste para passar.** Ele existe para avisar que um documento sigiloso pode chegar a um cliente.
