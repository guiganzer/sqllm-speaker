# Validação externa — Sakila de terceiros

A fonte é o benchmark MIT `text2sql-benchmark-id`, separado de todo treino e do benchmark interno Pagila.

## Fonte e inspeção

A revisão `fab6e4d40da5f58dd42fe5072a01ca6305835d88` fica localmente em `data/raw/`. O subconjunto Sakila contém 30 perguntas em indonésio e inglês, SQL MySQL, resultados esperados e seis categorias.

```powershell
uv run python scripts/inspect_external_sakila_benchmark.py `
  --report artifacts/reports/external-sakila-fab6e4d40da5.json
```

## Porta derivada para o produto

O runtime do projeto é PostgreSQL/Pagila. Portanto, o comando abaixo transpõe cada SQL MySQL para PostgreSQL, aplica somente as quatro equivalências documentadas no manifesto e executa com `sqllm_readonly`.

```powershell
uv run python scripts/port_external_sakila_to_pagila.py
```

A execução canônica atual está em `data/evaluations/external/sakila-third-party-fab6e4d40da5-pg-v3/`: **30 de 30** consultas aceitaram a política e executaram.

## Limites de interpretação

- O SQL e `expected_rows` originais continuam sendo gabaritos do Sakila/MySQL de terceiros.
- O SQL PostgreSQL e os hashes de resultado Pagila são derivados locais; não se deve comparar seus valores diretamente aos `expected_rows` originais.
- As perguntas externas ainda estão em indonésio/inglês. Uma tradução PT-BR futura será outro artefato derivado, congelado e avaliado separadamente.
- Nenhum dos 30 itens — original ou derivado — pode entrar no corpus de especialização ou na validação durante o treino.

Assim, esta suíte mede generalização de SQL em consultas de terceiros, enquanto o benchmark Pagila/PT-BR de 24 itens continua medindo a especialização do produto.