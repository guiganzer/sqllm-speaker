# Pagila v3 — enriquecimento semântico

## Objetivo

A v3 mantém o modelo-base e continua o adapter v2. O foco é reduzir erros semânticos — joins, projeções, agrupamentos, ordenação e limites — sem iniciar comparação entre modelos.

## Dados e isolamento

- Fonte: Pagila público, revisão `v18-fc7a867`.
- Edição: `v3`.
- Total: 2.066 perguntas PT-BR.
- Treino: 1.579 exemplos.
- Validação: 487 exemplos.
- SQLs únicas executadas: 795.
- Famílias: 40.
- Fingerprint: `3a4a4b93d6f6638ee5576945b60cddb84bc557e0f7ab55b6bf39f4bcb794a7c7`.
- SHA-256 treino: `c0ee0e7eb011866762b85d01975af2a652013a9bf914b8b8e93ce71d0bd9e6b2`.
- SHA-256 validação: `4428a4539f0e219f34ef844f56f5d84a9648148de8d7dab448a8857000b220e1`.

As famílias `v3-actor-prefix-rating`, `v3-category-revenue-top` e `v3-rental-day-store` são exclusivas da validação. As 24 perguntas internas congeladas e os 30 itens Sakila externos continuam fora do corpus. A parcela v1/v2 funciona como replay de competências anteriores.

Cada uma das 795 SQLs distintas foi executada com `sqllm_readonly`. Paráfrases da mesma intenção reutilizam a validação daquela SQL. O contexto tem 141–593 tokens (média 478,6), portanto nenhuma amostra excede o limite de 1.024 tokens.

## Contexto enriquecido

A v3 usa `pagila-enriched-v1`:

- colunas e tipos;
- cardinalidade;
- chaves primárias;
- chaves estrangeiras;
- valores categóricos somente de uma lista pública permitida.

O contexto básico de v1/v2 foi preservado para que esses experimentos possam ser reproduzidos. Hints de valores não são descobertos automaticamente em bancos futuros.

## Baseline estrutural da v2

O relatório foi calculado sobre as mesmas 24 perguntas congeladas:

| Componente | Acertos |
| --- | ---: |
| Relações | 23/24 (95,83%) |
| Agregações | 23/24 (95,83%) |
| Limite | 21/24 (87,50%) |
| Predicados | 18/24 (75,00%) |
| Agrupamento | 13/24 (54,17%) |
| Joins | 12/24 (50,00%) |
| Projeção | 7/24 (29,17%) |
| Ordenação | 6/24 (25,00%) |

Isso confirma que a prioridade não é mais parse: é estrutura semântica, especialmente ordenação, projeção, joins e agrupamento.

## Runtime agentic

A sessão modelada passa a usar contexto enriquecido por padrão e pode gerar de um a cinco candidatos por beam search determinístico. Um ranker explícito pontua sinais da pergunta, como `COUNT`, `SUM`, `AVG`, `GROUP BY`, direção da ordenação, granularidade mensal e `LIMIT`. Política de leitura, escopo e reparo limitado continuam obrigatórios.

## Treino

O smoke continua o adapter v2 e não baixa novamente o modelo se o cache local estiver íntegro:

```powershell
uv run python scripts/train_phase_02_pagila.py --initial-adapter artifacts/runs/phase-02-pagila-v2-768f209d9ea8 --train-file data/processed/phase-03/pagila-v18-fc7a867-pt-v3/train.jsonl --validation-file data/processed/phase-03/pagila-v18-fc7a867-pt-v3/validation.jsonl --run-name phase-03-pagila-v3-smoke --max-train-samples 64 --max-validation-samples 32 --max-steps 2 --epochs 1 --learning-rate 2e-5 --eval-steps 2 --save-steps 2
```

Se o smoke concluir, execute duas épocas. A taxa menor e duas épocas são deliberadas porque o adapter já passou pelas fases geral, v1 e v2:

```powershell
uv run python scripts/train_phase_02_pagila.py --initial-adapter artifacts/runs/phase-02-pagila-v2-768f209d9ea8 --train-file data/processed/phase-03/pagila-v18-fc7a867-pt-v3/train.jsonl --validation-file data/processed/phase-03/pagila-v18-fc7a867-pt-v3/validation.jsonl --run-name phase-03-pagila-v3 --epochs 2 --learning-rate 2e-5 --logging-steps 5 --eval-steps 50 --save-steps 50
```

Não iniciar o treino completo se o smoke produzir CUDA OOM, exemplos tokenizados vazios ou perda não finita.

## Avaliação após o treino

Repetir o benchmark congelado sob o mesmo contrato básico e candidato único mede o ganho do adapter sem misturar ganhos do runtime:

```powershell
uv run python scripts/evaluate_pagila_phase_01_author.py --adapter-path artifacts/runs/phase-03-pagila-v3-768f209d9ea8 --label phase-03-pagila-author-v3 --max-examples-per-run 4 --resume
```

Repita o comando até `complete: true`. Depois:

```powershell
uv run python scripts/analyze_pagila_sql_components.py --predictions artifacts/evaluations/phase-03-pagila-author-v3/predictions.jsonl
```

Critério de avanço: preservar parse/escopo e execução da v2, superar 5/24 resultados idênticos e melhorar principalmente projeção, ordenação, joins e agrupamento.
