# Sessão agentic com adapter — Pagila

Esta sessão usa o adapter QLoRA da fase 1 como **autor SQL**. O adapter é carregado em 4-bit somente durante a execução e responde a partir da pergunta e do contexto compacto de DDL do Pagila.

## Execução

Com Docker Desktop e o Pagila local ativos:

```powershell
uv run python scripts/run_pagila_model_agentic_session.py `
  --question "Quantos filmes existem no catálogo?" `
  --tables film `
  --max-rows 5 `
  --max-new-tokens 128
```

`--tables` ainda é a saída controlada do especialista de schema: nesta etapa, ela deve ser fornecida explicitamente como relações candidatas separadas por vírgula. A seleção autônoma de relações é uma medição separada e não é mascarada por este comando.

## Fluxo e guardiões

1. O especialista obtém somente o DDL das relações candidatas.
2. O compilador cria um único contexto dentro do orçamento configurado (6.000 caracteres por padrão).
3. O adapter da fase 1 produz SQL determinístico (`do_sample=False`) com o mesmo contrato de prompt usado no treino geral.
4. O guardião de escopo bloqueia relações que não foram entregues ao modelo.
5. A política bloqueia escrita e múltiplas statements.
6. O executor roda como `sqllm_readonly`, com timeout de 5 segundos e limite de linhas.
7. Falha de execução pode receber um reparo com erro sanitizado; há no máximo um reparo.

O comando imprime candidatos, estágio e resultado apenas no terminal. Não grava perguntas ou resultados no Git.

## Validação registrada

Em 16 de setembro de 2026, a pergunta acima gerou `SELECT COUNT(*) FROM public.film` e retornou `1000`. Isso valida a integração técnica; não é uma medida de qualidade geral. A medição pública comparável está em [pagila-author-benchmark.md](pagila-author-benchmark.md).