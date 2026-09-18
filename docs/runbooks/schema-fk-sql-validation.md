# Runbook — prompt e validação SQL por relation pack

## Finalidade

`scripts/validate_schema_sql.py` mostra o schema mínimo enviado ao autor SQL e, opcionalmente, valida e executa uma consulta no espelho SQLite do Olist. A conexão usa `mode=ro`, `PRAGMA query_only`, política lexical de leitura, parse com SQLGlot, restrição às tabelas do pack, limite de linhas e limite de instruções da máquina virtual SQLite.

## Mostrar contexto e prompt

```powershell
uv run python scripts/validate_schema_sql.py `
  --catalog configs/datasets/olist.json `
  --pack orders-payments `
  --question "Qual é o valor total pago em pedidos entregues?"
```

## Validar e executar SQL

```powershell
uv run python scripts/validate_schema_sql.py `
  --catalog configs/datasets/olist.json `
  --pack orders-payments `
  --question "Qual é o valor total pago em pedidos entregues?" `
  --sql "SELECT ROUND(SUM(op.payment_value), 2) AS total_pago FROM orders AS o JOIN order_payments AS op ON op.order_id = o.order_id WHERE o.order_status = 'delivered'" `
  --max-rows 10
```

Uma SQL pode ser fornecida por arquivo com `--sql-file caminho.sql`. O limite padrão é 50 milhões de passos virtuais; reduza ou aumente explicitamente com `--max-vm-steps` conforme a consulta, sem remover as demais barreiras.

## Resultado esperado do teste de integração

Em 17 de setembro de 2026, o exemplo acima foi aprovado e executado no espelho Olist, retornando `15422461.77`.

## Limites atuais

- A execução genérica implementada nesta etapa é SQLite.
- O catálogo Logistics já renderiza contexto PostgreSQL, mas a execução depende da ingestão pendente em um banco local dedicado.
- O script valida uma SQL fornecida; a integração direta com o modelo será feita após congelar os holdouts.
