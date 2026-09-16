# Experimento Pagila v3 smoke — 16 de setembro de 2026

## Resultado

Status: concluído e aprovado.

- Modelo-base: `Qwen/Qwen3-4B-Thinking-2507`.
- Revisão: `768f209d9ea81521153ed38c47d515654e938aea`.
- Adapter inicial: `phase-02-pagila-v2-768f209d9ea8`.
- Treino: 64 exemplos tokenizados, nenhum descartado.
- Validação: 32 exemplos tokenizados, nenhum descartado.
- Passos de otimização: 2.
- Época efetiva: 0,5.
- Taxa de aprendizado: `2e-5`.
- Perda de treino: 0,153642.
- Perda de validação: 0,287430.
- Tempo de treino: 63,17 s.
- Tempo da avaliação final: 13,47 s.
- Artefato local: `artifacts/runs/phase-03-pagila-v3-smoke-768f209d9ea8`.

## Decisão

O smoke atende aos critérios de continuidade: CUDA e quantização carregaram, não ocorreu OOM, as perdas são finitas, os conjuntos permaneceram não vazios e o adapter foi salvo. O treino integral de duas épocas está liberado, sempre partindo do adapter v2 — o adapter smoke não deve ser usado como ponto inicial.

O aviso de requisições não autenticadas ao Hugging Face Hub não afeta a validade do experimento; o modelo já está em cache. Um `HF_TOKEN` é opcional para elevar limites de download.
