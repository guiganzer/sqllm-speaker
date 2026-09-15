# Runbook — treino geral completo da fase 1

## Finalidade

Treinar uma época do adapter QLoRA com o conjunto público em português, com checkpoints recuperáveis e uma amostra fixa de validação. O conjunto de 7.838 exemplos isolados por schema continua reservado para o benchmark final; não é usado integralmente em cada checkpoint.

## Pré-condições

1. Execute os testes: `uv run python -m unittest discover -s tests -t . -v`.
2. Confirme GPU e espaço em disco com `uv run python scripts/gpu_preflight.py`.
3. Garanta que o repositório esteja limpo: `git status --short` não deve listar arquivos.

## Calibração de duração

Antes do treino longo, execute 100 passos em 2.048 exemplos e registre a taxa observada. Ela mede a velocidade com uma amostra mais representativa que o smoke test.

```powershell
uv run python scripts/train_phase_01.py --run-name phase-01-calibration --max-train-samples 2048 --max-validation-samples 128 --max-steps 100 --eval-steps 100 --save-steps 100
```

A calibração foi concluída em 15 de setembro de 2026: 100 passos em 906,076 s (`0,110` passo/s), com `1,766` amostra/s. Para 70.551 exemplos, batch 1 e acumulação 16, uma época equivale a aproximadamente 4.410 passos. A projeção é de cerca de **11h20** incluindo as avaliações; reserve 12 horas para absorver checkpoints e variação do Windows. O manifesto está em `docs/experiment-manifests/phase-01-calibration-2026-09-15.md`.

## Treino completo recomendado

```powershell
uv run python scripts/train_phase_01.py --run-name phase-01-general-e1 --epochs 1 --max-validation-samples 512 --logging-steps 10 --eval-steps 500 --save-steps 500 --save-total-limit 3
```

O comando mostra perda e progresso no terminal. Também grava `artifacts/logs/phase-01-general-e1-<revisão>.log`, checkpoints em `artifacts/runs/phase-01-general-e1-<revisão>/checkpoint-*` e um `running-manifest.json` desde o início.

Em outro PowerShell, acompanhe a GPU e o log:

```powershell
nvidia-smi -l 2
Get-Content .\artifacts\logs\phase-01-general-e1-768f209d9ea8.log -Wait
```

## Retomada após interrupção

Escolha o checkpoint mais recente e repita exatamente os mesmos parâmetros, acrescentando seu caminho:

```powershell
uv run python scripts/train_phase_01.py --run-name phase-01-general-e1 --epochs 1 --max-validation-samples 512 --logging-steps 10 --eval-steps 500 --save-steps 500 --save-total-limit 3 --resume-from-checkpoint .\artifacts\runs\phase-01-general-e1-768f209d9ea8\checkpoint-500
```

Não altere modelo, revisão, dados, seed ou hiperparâmetros ao retomar. Ao terminar, `run-manifest.json` substitui a marca provisória com métricas de treino e validação.

## Avaliação por geração

Primeiro avalie o modelo-base; depois, o adapter da execução concluída. A amostra é determinística e estratificada por complexidade.

```powershell
uv run python scripts/evaluate_phase_01.py --run-name phase-01-base-eval --sample-size 512
uv run python scripts/evaluate_phase_01.py --run-name phase-01-general-e1-eval --adapter-path .\artifacts\runs\phase-01-general-e1-768f209d9ea8 --sample-size 512
```

Os relatórios ficam em `artifacts/evaluations/<run-name>/report.json`; as previsões auditáveis ficam em `predictions.jsonl`. Compare parse, saída somente SQL, política read-only e referências ao schema. A perda do `Trainer` sozinha não aprova o modelo.
