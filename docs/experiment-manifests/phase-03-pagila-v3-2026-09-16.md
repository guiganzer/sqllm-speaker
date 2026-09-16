# Experimento Pagila v3 — 16 de setembro de 2026

## Resultado do treino

Status: concluído tecnicamente e liberado para benchmark; promoção ainda depende da avaliação congelada.

- Modelo-base: `Qwen/Qwen3-4B-Thinking-2507`.
- Revisão: `768f209d9ea81521153ed38c47d515654e938aea`.
- Adapter inicial: `phase-02-pagila-v2-768f209d9ea8`.
- Adapter produzido: `phase-03-pagila-v3-768f209d9ea8`.
- Treino: 1.579 exemplos.
- Validação: 487 exemplos de famílias isoladas.
- Épocas: 2.
- Passos de otimização: 198.
- Taxa inicial: `2e-5`, com decaimento.
- Perda média de treino: 0,010463.
- Perda final de validação: 0,203507.
- Tempo de treino: 4.717,01 s (1h18m37s).
- Velocidade: 0,669 amostra/s e 0,042 passo/s.
- Adapter: 132.187.888 bytes.
- Testes pós-treino: 59/59 aprovados.

## Curva

| Passo | Época | Eval loss |
| ---: | ---: | ---: |
| 50 | 0,507 | 0,222756 |
| 100 | 1,010 | 0,205318 |
| 150 | 1,517 | 0,204681 |
| 198 | 2,000 | 0,203507 |

A validação melhorou monotonicamente e não mostrou reversão de overfitting. O ganho após o passo 100 foi pequeno, indicando platô, mas ainda positivo. Os gradientes permaneceram finitos e baixos (máximo observado aproximadamente 0,637), sem instabilidade. A perda de treino muito baixa frente à validação é esperada em parte pelas paráfrases que compartilham SQL; por isso, ela não basta para promover o modelo.

## Decisão

O treino é tecnicamente saudável e está liberado para o benchmark congelado. A promoção exige preservar pelo menos 23/24 em parse/escopo e 22/24 em execução, superar 5/24 resultados idênticos da v2 e apresentar melhoria estrutural relevante, sobretudo em projeção, ordenação, joins ou agrupamento.
