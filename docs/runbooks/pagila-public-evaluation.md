# Avaliação pública — Pagila

A avaliação é gerada por templates programáticos e executada contra o Pagila local. Ela é uma verificação de runtime e schema, não um dataset humano-curado de treinamento.

## Geração

Com o contêiner ativo:

```powershell
uv run python scripts/generate_pagila_evaluation.py
```

O comando cria em `data/evaluations/pagila/v18-fc7a867/`, área ignorada pelo Git:

- `evaluation.jsonl`: pergunta em português, SQL de referência, categoria, número de linhas e hash do resultado;
- `report.json`: resumo agregado, sem valores retornados pelo banco.

A geração recusa qualquer SQL que não passe na política somente leitura, não faça parse como PostgreSQL ou falhe na execução.

## Cobertura inicial

O conjunto verifica contagens, filtros, agregações, ordenação, joins, datas, views e colunas descritivas do Pagila. Ele é intencionalmente pequeno e reproduzível: valida o runtime antes de gerar dados de especialização em maior escala.

## Estado e próxima etapa

O compilador de contexto e a sessão com adapter já foram concluídos. O conjunto de 24 consultas permanece congelado para avaliação, inclusive no [benchmark do autor SQL](pagila-author-benchmark.md), e não pode entrar no corpus de especialização.

A próxima etapa é gerar um corpus público Pagila separado, validá-lo por execução e registrar seu manifesto antes de qualquer ajuste fino.
