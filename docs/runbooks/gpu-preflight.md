# Runbook — Preflight da GPU

## Execução

```powershell
uv run python scripts/gpu_preflight.py
```

O script usa o PyTorch CUDA instalado no `.venv` e registra o resultado em `artifacts/reports/gpu-preflight.json`.

## Critérios para o projeto

- `cuda_available` deve ser `true`;
- VRAM total mínima: 7 GiB;
- a GPU deve reportar suporte BF16 para manter a configuração inicial de QLoRA;
- `bitsandbytes_version` deve estar presente, confirmando a biblioteca de quantização do QLoRA;
- o nome da GPU deve corresponder à RTX 4070 Laptop observada no inventário inicial.

O wheel instalado é o PyTorch 2.7.0 com CUDA 12.8, obtido do índice oficial do PyTorch. As bibliotecas CUDA necessárias são distribuídas pelo wheel; não há requisito de toolkit CUDA local. A orientação oficial de instalação do PyTorch para Windows é: https://pytorch.org/get-started/locally/.
