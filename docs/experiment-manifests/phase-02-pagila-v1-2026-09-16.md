# Fase 2 Pagila v1 — resultado de especialização

## Identidade do experimento

- Data de conclusão: 16 de setembro de 2026.
- Modelo base: Qwen/Qwen3-4B-Thinking-2507.
- Revisão imutável: 768f209d9ea81521153ed38c47d515654e938aea.
- Adapter inicial: artifacts/runs/phase-01-general-e1-768f209d9ea8.
- Adapter final: artifacts/runs/phase-02-pagila-v1-768f209d9ea8.
- Dados: Pagila público v18 na revisão fc7a867, PostgreSQL.
- Corpus: 149 exemplos parametrizados e executados; 119 treino, 30 validação.
- Fingerprint do corpus: 528b30e04d0cf8c114cef1a698e10592d5ee89576753ed1c948717e1b1057f8f.
- Exclusões confirmadas: as 24 perguntas internas Pagila e os 30 itens externos Sakila não participaram do treino.

## Treinamento

O QLoRA continuou o adapter da fase 1; não criou um LoRA novo.

| Parâmetro | Valor |
| --- | ---: |
| Épocas | 3 |
| Passos do otimizador | 24 |
| Learning rate inicial | 5e-5 |
| Comprimento máximo | 1024 |
| Perda final de treino | 0,2209 |
| Perda final de validação | 0,3122 |
| Duração | 398,5 s |

O smoke test anterior foi concluído com 32 exemplos, 8 validações e 2 passos.

## Benchmark congelado do autor SQL

O mesmo benchmark público Pagila foi aplicado ao adapter da fase 1 e ao adapter especializado. O contrato é idêntico nos dois lados: 24 perguntas, fingerprint 2cdd251a51a650307e055c6c42ff04cd29c5a3c811a8a0e3e5fd8da79c6c1b10, contexto de até 6.000 caracteres e geração de até 128 tokens. A seleção de relações continua sendo extraída da SQL de referência somente para isolar o autor SQL.

| Métrica | Fase 1 | Fase 2 | Delta |
| --- | ---: | ---: | ---: |
| Parse e escopo válidos | 24/24 (100%) | 23/24 (95,83%) | -1 |
| Política permitida | 24/24 (100%) | 23/24 (95,83%) | -1 |
| SQL executado | 16/24 (66,67%) | 22/24 (91,67%) | +6 |
| Resultado idêntico | 1/24 (4,17%) | 3/24 (12,50%) | +2 |
| Exact match canônico | 0/24 (0%) | 1/24 (4,17%) | +1 |

Artefatos locais ignorados pelo Git:

- artifacts/evaluations/phase-01-pagila-author-baseline/report.json
- artifacts/evaluations/phase-02-pagila-author/report.json
- artifacts/runs/phase-02-pagila-v1-768f209d9ea8/run-manifest.json

## Decisão

A especialização v1 melhorou materialmente a capacidade de produzir SQL executável e triplicou os resultados equivalentes no benchmark congelado. Ela não está aprovada como resultado final para uso autônomo: há uma regressão de escopo e 21 de 24 consultas ainda não devolvem o mesmo resultado da referência.

A próxima iteração deve manter todos os benchmarks congelados e ampliar somente o corpus de treino público com famílias que cubram joins, LEFT JOIN, ordenação, limites, aliases, agregações condicionais e uso de views. Em seguida, repetir a mesma comparação. Não tratar a perda de validação como substituta das métricas de execução e resultado.
