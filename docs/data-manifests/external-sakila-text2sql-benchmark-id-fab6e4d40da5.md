# Manifesto de dados — validação externa Sakila Text-to-SQL

## Fonte

| Campo | Valor |
|---|---|
| Repositório | `Galih-Hermawan-Unikom/text2sql-benchmark-id` |
| URL | https://github.com/Galih-Hermawan-Unikom/text2sql-benchmark-id |
| Revisão fixada | `fab6e4d40da5f58dd42fe5072a01ca6305835d88` |
| Licença | MIT, copyright Galih Hermawan (2025) |
| Arquivo canônico | `gold-standard.json` |
| Subconjunto adotado | 30 itens com `db: sakila` |
| Linguagem das perguntas | indonésio e inglês |
| Dialeto do SQL de referência | MySQL |

A cópia bruta fica em `data/raw/text2sql-benchmark-id/fab6e4d40da5/`, área ignorada pelo Git. O script `scripts/inspect_external_sakila_benchmark.py` verifica IDs, campos obrigatórios, contagem e hash antes de produzir um relatório local.

## Uso autorizado e isolamento

Esta é uma **suíte de validação externa**, não uma fonte de treino. Seus 30 itens são excluídos de:

- corpus de especialização Pagila;
- benchmark interno Pagila de 24 perguntas;
- qualquer validação interna usada durante o treino.

O benchmark deve executar o SQL original contra o schema Sakila/MySQL distribuído pela fonte. Não é válido comparar diretamente seus `expected_rows` ao Pagila/PostgreSQL: há divergências de dialeto, versão e dados. Uma eventual versão em português ou porta para PostgreSQL será um artefato derivado, versionado e medido separadamente, nunca apresentado como gabarito original de terceiros.

## Cobertura

São cinco casos para cada categoria: `Aggregation`, `Comparison`, `Join`, `Lookup / Filter`, `Nested / Subquery` e `Superlative`. Cada item traz SQL-gabarito, resultados esperados e regra de ordenação.
## Porta PostgreSQL/Pagila derivada

A versão derivada canônica local é `data/evaluations/external/sakila-third-party-fab6e4d40da5-pg-v3/`. Em 16 de setembro de 2026, os **30/30** SQLs foram transpostos e executados pelo papel `sqllm_readonly`.

A transformação usa SQLGlot (`mysql` para `postgres`) e quatro equivalências de schema/dialeto revisadas:

| Casos | Equivalência aplicada |
|---|---|
| `SAK-J2-01`, `SAK-J2-04`, `SAK-J2-05` | `rental_date` → `LOWER(rental_period)` |
| `SAK-S6-02` | `HAVING` sem agrupamento, aceito pelo MySQL, → `WHERE` PostgreSQL equivalente |

O hash do `gold-standard.json` é `2611eb2835c7cd9a25c671b372ba68203fe56bcdbf0111bbbe344cd7bab7c015`. Os hashes de resultado do Pagila são referências derivadas locais. Os valores esperados da fonte MySQL não são usados como oráculo do Pagila.