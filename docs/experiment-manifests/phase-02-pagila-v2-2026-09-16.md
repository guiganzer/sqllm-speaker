# Fase 2 Pagila v2 — resultado da especialização incremental

## Identidade

- Data: 16 de setembro de 2026.
- Modelo base: Qwen/Qwen3-4B-Thinking-2507.
- Revisão: 768f209d9ea81521153ed38c47d515654e938aea.
- Adapter inicial: artifacts/runs/phase-02-pagila-v1-768f209d9ea8.
- Adapter final: artifacts/runs/phase-02-pagila-v2-768f209d9ea8.
- Corpus: Pagila público v18, edição v2.
- Corpus validado: 212 exemplos, 165 treino, 47 validação.
- Fingerprint do corpus: 71ae988b0fefdb4f7a149d743ff6cc463e63eacf23dd916e955beec9e84f4e94.
- Exclusões preservadas: benchmark interno Pagila e suíte externa Sakila.

## Treinamento

| Parâmetro | Valor |
| --- | ---: |
| Épocas | 3 |
| Passos do otimizador | 33 |
| Learning rate inicial | 5e-5 |
| Perda final de treino | 0,0501 |
| Perda final de validação | 0,2994 |
| Duração | 921,8 s |

## Comparação no benchmark congelado

O benchmark tem 24 perguntas, fingerprint 2cdd251a51a650307e055c6c42ff04cd29c5a3c811a8a0e3e5fd8da79c6c1b10, contexto máximo de 6.000 caracteres e até 128 tokens gerados. A avaliação v2 foi concluída uma única vez com 24 identificadores únicos.

| Métrica | Fase 1 | Pagila v1 | Pagila v2 |
| --- | ---: | ---: | ---: |
| Parse e escopo válidos | 24/24 | 23/24 | 23/24 |
| Política permitida | 24/24 | 23/24 | 23/24 |
| SQL executado | 16/24 | 22/24 | 22/24 |
| Resultado idêntico | 1/24 | 3/24 | 5/24 |
| Exact match canônico | 0/24 | 1/24 | 1/24 |

Contra v1, v2 manteve execução e escopo, e adicionou dois resultados idênticos. Contra a fase 1, executa seis consultas a mais e obtém quatro resultados idênticos a mais.

Acertos de resultado adicionados pela v2 incluem a consulta de atores com mais filmes, cidades por país e receita por categoria. Falhas remanescentes se concentram em requisitos semânticos finos: preservar todas as categorias em joins externos, projetar somente os campos solicitados, aplicar o limite correto, agrupamentos temporais e agregações condicionais.

## Decisão

A v2 é o melhor adapter do projeto até aqui e passa a ser o candidato ativo de inferência experimental. Ele não é aprovado para execução autônoma: o runtime agentic continua obrigatório e as métricas de resultado ainda são 5/24. A próxima melhoria deve priorizar geração estruturada ou reparo orientado por execução, não apenas ampliar exemplos de ajuste fino.

Artefatos locais:

- artifacts/runs/phase-02-pagila-v2-768f209d9ea8/run-manifest.json
- artifacts/evaluations/phase-02-pagila-author-v2/report.json
