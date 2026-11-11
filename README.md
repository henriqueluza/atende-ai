# atende-ai

Plataforma de conhecimento e atendimento com IA para pequenos negócios.

O sistema tem duas metades ligadas por um contrato MCP:

1. **Núcleo de conhecimento:** recebe os documentos do negócio, extrai e indexa o conteúdo e responde buscas (RAG).
2. **Agente de atendimento:** conversa com os clientes pelo WhatsApp, consulta o núcleo pelas ferramentas MCP e executa ações (agenda, cadastro, pagamento).

## Estrutura

```
services/
  core-api/      núcleo: ingestão, extração, RAG
  mcp-server/    ferramentas expostas para agentes
  agent/         agente de WhatsApp
pipelines/       orquestração e jobs de dados
ml/              treino, avaliação, modelos
infra/           Docker, Terraform, CI
docs/
  adr/           decisões de arquitetura
  semanal/       resumo semanal (roteiro da apresentação)
```

## Como rodar

> A preencher quando o esqueleto de ponta a ponta existir. A meta é subir tudo com um comando (`docker compose up`).

## Como contribuir

Leia o [CONTRIBUTING.md](CONTRIBUTING.md) antes do primeiro PR. Resumo: ninguém envia direto na `main`, todo trabalho entra por PR pequeno, com CI verde e uma aprovação.

## Equipe

| Área | Dono | Revisor da vez |
|---|---|---|
| Ingestão e pipeline | a definir | a definir |
| Busca e RAG | a definir | a definir |
| ML e extração | a definir | a definir |
| MCP | a definir | a definir |
| Agente | a definir | a definir |
| Plataforma (CI, infra, avaliação) | a definir | a definir |
