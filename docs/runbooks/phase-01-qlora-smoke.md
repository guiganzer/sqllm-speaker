# Runbook — Smoke test QLoRA da fase 1

## Objetivo

Executar cinco passos de treino antes do experimento completo. O teste confirma download do modelo, compatibilidade do template de chat, tokenização, quantização 4-bit, LoRA, gradientes e checkpoints.

## Execução observável

```powershell
uv run python scripts/train_phase_01.py --run-name phase-01-smoke --max-train-samples 128 --max-validation-samples 32 --max-steps 5
```

O progresso aparece no terminal e é gravado em `artifacts/logs/phase-01-smoke-<revisão>.log`. O adapter e o manifesto ficam em `artifacts/runs/phase-01-smoke-<revisão>/`.

## Proteções

- A revisão do modelo é resolvida pela API do Hugging Face e gravada no manifesto do experimento.
- Apenas a resposta do assistente (SQL) contribui para a perda; schema e pergunta são mascarados com `-100`.
- O modelo é carregado em NF4, computa em BF16 e usa adapter LoRA de rank 16.
- A API instalada do Transformers recebe a proporção de aquecimento em `warmup_steps=0.03`; não usar o parâmetro legado `warmup_ratio`.
- Os artefatos são ignorados pelo Git; métricas aprovadas devem ser resumidas em `PROJECT_CONTEXT.md`.

## Resultado registrado

O smoke test de 15 de setembro de 2026 foi aprovado com o modelo `Qwen/Qwen3-4B-Thinking-2507` na revisão `768f209d9ea81521153ed38c47d515654e938aea`. O registro completo está em `docs/experiment-manifests/phase-01-smoke-2026-09-15.md`.

## Após aprovação

Executar o treino completo sem `--max-steps` e sem os limites de amostras, sempre a partir de um commit limpo.
