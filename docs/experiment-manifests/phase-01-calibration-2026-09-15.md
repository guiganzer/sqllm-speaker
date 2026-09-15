# Manifesto de experimento — calibração da fase 1

## Identificação

| Campo | Valor |
|---|---|
| Término (UTC) | 2026-09-15T02:35:14.131200+00:00 |
| Modelo | `Qwen/Qwen3-4B-Thinking-2507` |
| Revisão | `768f209d9ea81521153ed38c47d515654e938aea` |
| Dados | `emdemor/sql-create-context-pt` na revisão `ee31747c93bdf859c57468ec1f28c4360cc84b1b` |
| Hardware | RTX 4070 Laptop, 8 GiB VRAM, QLoRA NF4/BF16 |

## Configuração

- 100 passos, 2.048 exemplos candidatos de treino e 128 de validação.
- Batch por dispositivo 1, acumulação de gradiente 16, contexto de 1.024 tokens.
- Avaliação e checkpoint no passo 100.
- Taxa de aprendizado 0,0002; warmup de 3%; seed 42.

## Métricas observadas

| Métrica | Valor |
|---|---:|
| Tempo de treino | 906,076 s (15 min 6 s) |
| Passos por segundo | 0,110 |
| Amostras por segundo | 1,766 |
| Perda de treino | 0,2682 |
| Perda de validação | 0,0953 |
| Tempo de avaliação (128 exemplos) | 17,424 s |

## Projeção e decisão

Uma época completa tem aproximadamente `ceil(70.551 / 16) = 4.410` passos. Pela taxa medida, o treino ocupa cerca de 11h08; as avaliações periódicas de 512 exemplos acrescentam aproximadamente 9 minutos. A janela operacional aprovada para uma época é **12 horas**.

**Aprovado para uma época completa.** As perdas desta calibração não são métricas de qualidade final, porque a execução foi curta e não usou o benchmark de geração isolado. O adapter e o checkpoint locais ficam em `artifacts/runs/phase-01-calibration-768f209d9ea8/` e não entram no Git.
