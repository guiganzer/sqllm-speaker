# Pagila v2 — plano de especialização incremental

## Motivação

A comparação v1 elevou SQL executável de 66,67% para 91,67%, mas expôs falhas em projeção, ordenação, limites, aliases e joins extensos. A v2 amplia apenas o corpus público Pagila; os benchmarks interno Pagila e externo Sakila permanecem bloqueados para treino.

## Corpus

- Edição: v2.
- Fonte: Pagila público v18, revisão fc7a867.
- Total: 212 exemplos executados e validados.
- Treino: 165 exemplos.
- Validação: 47 exemplos, separados por famílias.
- Fingerprint: 71ae988b0fefdb4f7a149d743ff6cc463e63eacf23dd916e955beec9e84f4e94.

As famílias novas cobrem joins explícitos e externos, aliases, agregações com filtros, ordenação estável, limites, intervalos temporais PostgreSQL e as views customer_list e sales_by_film_category.

## Continuidade do modelo

A v2 continua o adapter final da v1. Ela não volta ao adapter geral da fase 1 e não inicia um novo LoRA.

## Execução

Na raiz do repositório, execute primeiro o smoke:

~~~powershell
uv run python scripts/train_phase_02_pagila.py --initial-adapter artifacts/runs/phase-02-pagila-v1-768f209d9ea8 --train-file data/processed/phase-02/pagila-v18-fc7a867-pt-v2/train.jsonl --validation-file data/processed/phase-02/pagila-v18-fc7a867-pt-v2/validation.jsonl --run-name phase-02-pagila-v2-smoke --max-train-samples 64 --max-validation-samples 16 --max-steps 2 --eval-steps 2 --save-steps 2
~~~

Após smoke bem-sucedido, execute:

~~~powershell
uv run python scripts/train_phase_02_pagila.py --initial-adapter artifacts/runs/phase-02-pagila-v1-768f209d9ea8 --train-file data/processed/phase-02/pagila-v18-fc7a867-pt-v2/train.jsonl --validation-file data/processed/phase-02/pagila-v18-fc7a867-pt-v2/validation.jsonl --run-name phase-02-pagila-v2 --epochs 3 --eval-steps 20 --save-steps 20
~~~

Depois, repetir o benchmark congelado com novo label e compará-lo primeiro com v1 e então com a fase 1. Aceitar somente um relatório completo com 24 identificadores únicos.
