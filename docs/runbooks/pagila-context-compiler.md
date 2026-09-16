# Compilador de contexto — Pagila

O compilador elimina o schema completo do prompt. A partir de uma consulta PostgreSQL, ele identifica tabelas e views referenciadas, ignora aliases de CTE e concatena somente os DDLs necessários dentro de um orçamento explícito de caracteres.

## Demonstração

```powershell
uv run python scripts/compile_pagila_context.py `
  --sql "SELECT category.name, COUNT(film_category.film_id) FROM category JOIN film_category USING (category_id) GROUP BY category.name" `
  --show-ddl
```

Por padrão, o orçamento é 6.000 caracteres. Se ele for excedido, o compilador falha em vez de truncar DDL e introduzir contexto inconsistente.

## Uso no fluxo agentic

- Na avaliação, o SQL de referência determina o contexto compacto.
- Na inferência, o especialista de schema seleciona relações candidatas antes do autor SQL.
- Depois da proposta SQL, o compilador confirma se a consulta usa somente relações cujo schema foi disponibilizado.

O componente não executa SQL e não lê dados; usa apenas metadados obtidos pela ferramenta `get_table_schema`.
