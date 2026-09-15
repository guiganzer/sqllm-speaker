# Runbook — Preparação dos dados da fase 1

## Objetivo

Transformar `emdemor/sql-create-context-pt` em JSONL de treino e validação, preservando DDL e SQL e registrando a revisão exata da origem.

## Execução

```powershell
uv run python scripts/prepare_phase_01.py
```

O comando obtém a revisão atual de `main`, grava uma cópia local em `data/raw/`, processa os exemplos e imprime um relatório. Dados brutos e JSONL processados permanecem fora do Git.

## Garantias aplicadas

- pergunta, DDL e SQL são obrigatórios;
- SQL precisa ser uma única statement parseável pelo SQLGlot;
- duplicatas de pergunta + schema + SQL são removidas;
- a divisão usa hash do schema: nenhum DDL idêntico aparece em treino e validação;
- exemplos acima de 16.000 caracteres em qualquer campo são rejeitados, sem truncamento;
- o relatório contém a revisão imutável, contagens e razões de rejeição.

## Saídas

- `data/raw/emdemor__sql-create-context-pt/<revisão>/`
- `data/processed/phase-01/<revisão>/train.jsonl`
- `data/processed/phase-01/<revisão>/validation.jsonl`
- `artifacts/reports/phase-01-data-<revisão>.json`

Após a primeira execução bem-sucedida, copiar a revisão e as métricas relevantes para `PROJECT_CONTEXT.md` antes de iniciar o treino.

## Verificação posterior

```powershell
uv run python scripts/verify_phase_01.py data/processed/phase-01/ee31747c93bd
```

O resultado deve indicar `overlapping_schema_groups: 0`.
