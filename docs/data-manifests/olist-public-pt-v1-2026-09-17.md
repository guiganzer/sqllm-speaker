# Manifesto — corpus Olist público PT-BR v1

Data de geração: 17 de setembro de 2026.

Este corpus fica reservado para a segunda rodada, após a rodada WikiSQL. Ele não será misturado antecipadamente ao treino geral.

## Origem e validação

- Fonte canônica: nove CSVs originais do Olist.
- Banco de validação: cópia local indexada do espelho SQLite, em `data/interim/olist-validation.sqlite`.
- Catálogo: `configs/datasets/olist.json`.
- Prompt: `sql-author-schema-fk-v1`.
- Geração: templates públicos PT-BR parametrizados a partir de valores existentes no banco.
- Validação: política read-only, parse, escopo do relation pack e execução SQLite.

O script `scripts/prepare_olist_validation_db.py` copia o espelho raw e cria índices apenas na cópia. Nenhum CSV nem banco raw é modificado.

## Resultado

| Tier | Exemplos | Proporção |
| --- | ---: | ---: |
| `small` | 72 | 60% |
| `medium` | 30 | 25% |
| `heavy` | 18 | 15% |
| Total | 120 | 100% |

- Treino: 89 exemplos; SHA-256 `25aac7c61bc307367d7bf548e401f7f92e31135d1a5703bbb22fbcaad525b568`.
- Validação: 31 exemplos; SHA-256 `87b8e894a40cebd153dd94744ce9b5fbe593856902e89808dfe68b5c7729a117`.
- Status: `validated` e `training_ready=true`.

Famílias reservadas integralmente para validação:

- `olist-payment-status-total`;
- `olist-customer-review-payment`;
- `olist-heavy-negative-commerce`.

## Reprodução

```powershell
uv run python scripts/prepare_olist_validation_db.py
uv run python scripts/generate_olist_curriculum.py
```

Os scripts recusam sobrescrever saídas existentes. Para reproduzir novamente, use novos caminhos explícitos; não apague artefatos anteriores sem revisar seus manifests.

## Gate de uso

O corpus está tecnicamente validado, mas só entra na rodada 2. A rodada 1 deve concluir WikiSQL PT-BR criativo, replay geral, smoke, treino e benchmark antes de promover qualquer adapter como base da rodada Olist.
