# Arquitetura agentic de Text-to-SQL

Um único modelo assume papéis com contexto e ferramentas mínimos; a orquestração e a segurança são código determinístico.

| Papel | Responsabilidade | Ferramentas | Saída |
|---|---|---|---|
| Orquestrador | Controla estado e limites. | Nenhuma | Próxima ação válida. |
| Especialista de schema | Descobre metadados necessários. | Perfil e schema | Chamadas de ferramenta. |
| Autor de SQL | Gera uma única consulta. | Nenhuma | SQL candidato. |
| Guardião | Aplica política read-only. | Nenhuma; determinístico | Aprovação/bloqueio. |
| Executor | Executa SQL aprovado. | Execução read-only | Linhas limitadas ou erro sanitizado. |
| Reparador | Corrige erro usando schema já obtido. | Nenhuma | Nova consulta. |
| Finalizador | Encerra em SQL, esclarecimento ou abstenção. | Nenhuma | Decisão verificável. |

```text
pergunta → descoberta do schema → SQL candidato → guardião
                                               ├─ bloqueado → finalizador
                                               └─ aprovado → execução read-only
                                                               ├─ sucesso → finalizador
                                                               └─ erro → reparador (máx. 2) → guardião
```

## Ferramentas

- `get_database_profile`: retorna dialeto e inventário autorizado, sem credenciais ou linhas de negócio.
- `get_table_schema(table_name)`: retorna DDL/metadados somente de tabela permitida.
- `execute_readonly_sql(sql, max_rows)`: usa credencial realmente read-only, limite de linhas e sanitiza erros.

## Limites

- máximo de dois reparos;
- uma statement por execução;
- somente `SELECT`, `WITH` e `EXPLAIN`;
- escrita, DDL, transações e comandos administrativos são bloqueados.

O código em `src/llm_to_sql/agentic/` contém contratos, política e máquina de estados. Qualquer integração real deve obedecer a essas transições.
