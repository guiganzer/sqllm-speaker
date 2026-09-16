# Avaliação Pagila v3 — 16 de setembro de 2026

## Contrato

- Benchmark interno congelado: 24 perguntas.
- Fingerprint: `2cdd251a51a650307e055c6c42ff04cd29c5a3c811a8a0e3e5fd8da79c6c1b10`.
- Mesmo modelo-base, revisão, relações candidatas, limite de contexto e geração determinística de candidato único usados na v2.
- Adapter: `phase-03-pagila-v3-768f209d9ea8`.

## Resultado especializado

| Métrica | v2 | v3 | Delta |
| --- | ---: | ---: | ---: |
| Parse e escopo | 23/24 | 24/24 | +1 |
| Política | 23/24 | 24/24 | +1 |
| Executadas | 22/24 | 22/24 | 0 |
| Resultado idêntico | 5/24 | 8/24 | +3 |
| Exact match canônico | 1/24 | 2/24 | +1 |

A v3 atingiu o critério especializado: preservou execução, recuperou escopo completo e elevou equivalência de resultado de 20,83% para 33,33%.

## Componentes SQL

| Componente | v2 | v3 | Delta |
| --- | ---: | ---: | ---: |
| Relações | 23/24 | 24/24 | +1 |
| Agregações | 23/24 | 23/24 | 0 |
| Agrupamento | 13/24 | 17/24 | +4 |
| Ordenação | 6/24 | 11/24 | +5 |
| Limite | 21/24 | 21/24 | 0 |
| Predicados | 18/24 | 17/24 | -1 |
| Joins | 12/24 | 9/24 | -3 |
| Projeção | 7/24 | 5/24 | -2 |

A melhoria estrutural é real em agrupamento e ordenação, mas não uniforme. Persistem inclusão de colunas não solicitadas, uso de `INNER JOIN` no lugar de `LEFT JOIN`, limites inventados, filtros inventados e confusão entre duração do filme e duração de locação.

## Regressão geral congelada

A amostra geral de 512 schemas foi repetida com os mesmos 128 tokens do baseline da fase 1.

| Métrica | Fase 1 | v3 | Delta |
| --- | ---: | ---: | ---: |
| Parse | 512/512 | 512/512 | 0 |
| Somente SQL | 512/512 | 512/512 | 0 |
| Política | 512/512 | 512/512 | 0 |
| Referências válidas ao schema | 502/512 (98,05%) | 454/512 (88,67%) | -48 (-9,38 p.p.) |
| Exact match | 328/512 (64,06%) | 236/512 (46,09%) | -92 (-17,97 p.p.) |

A repetição adicional com 192 tokens produziu as mesmas contagens, descartando o limite de geração como causa.

## Decisão

A v3 é uma melhoria especializada no Pagila, mas sofre regressão geral material. Ela não substitui o adapter geral e não deve ser promovida como padrão universal. O runtime Pagila pode avaliá-la explicitamente por caminho, mantendo as barreiras agentic; o padrão versionado permanece na v2 até uma iteração com replay geral recuperar o benchmark de 512 schemas.

A próxima iteração deve combinar exemplos Pagila difíceis com replay estratificado do corpus geral e medir ambos os benchmarks. Não continuar treinando apenas no corpus Pagila v3.
