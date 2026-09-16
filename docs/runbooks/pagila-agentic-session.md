# Sessão agentic real — Pagila

O runtime Pagila usa os papéis já definidos pelo projeto:

1. **Orquestrador** inicia a sessão e impõe as transições.
2. **Especialista de schema** obtém perfil e DDL das relações pedidas.
3. **Autor SQL** propõe uma única consulta.
4. **Guardião de política** bloqueia escrita e múltiplas statements em código determinístico.
5. **Executor** roda apenas com a conta local `sqllm_readonly`, `statement_timeout` de 5 segundos e até 1.000 linhas.
6. **Reparador** recebe apenas erro sanitizado e tem no máximo um ciclo.
7. **Finalizador** encerra sucesso, bloqueio ou reparo necessário.

## Demonstração

Com Docker Desktop e Pagila ativos:

```powershell
uv run python scripts/run_pagila_agentic_session.py `
  --question "Quantos filmes existem por categoria?" `
  --tables category,film_category `
  --sql "SELECT category.name AS categoria, COUNT(film_category.film_id) AS total_filmes FROM category JOIN film_category USING (category_id) GROUP BY category.name ORDER BY total_filmes DESC" `
  --max-rows 20
```

A CLI é o modo de depuração com SQL fornecido. Para usar o adapter treinado como autor SQL, consulte a [sessão modelada](pagila-model-agentic-session.md). A seleção autônoma de relações permanece uma etapa posterior, medida separadamente.

Nenhuma ferramenta aceita escrita: há defesa em três camadas — política lexical, encapsulamento de `SELECT` com limite e conta PostgreSQL sem privilégios de `CREATE`, `INSERT`, `UPDATE`, `DELETE` ou DDL.
