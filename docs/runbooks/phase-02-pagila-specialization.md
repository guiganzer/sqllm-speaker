# Fase 2 — especialização pública Pagila

## Objetivo

Continuar o adapter QLoRA concluído na fase 1, ensinando vocabulário e relações do Pagila em PostgreSQL. Esta fase não inicia um LoRA novo: ela carrega o adapter \`phase-01-general-e1-768f209d9ea8\` como treinável.

## Integridade experimental

O gerador cria exemplos em português a partir de famílias parametrizadas e executa cada SQL com a conta local \`sqllm_readonly\`.

- O corpus usa somente Pagila público na revisão documentada em \`docs/data-manifests/pagila-v18-fc7a867.md\`.
- As 24 perguntas do benchmark interno Pagila são verificadas e recusadas se houver igualdade de pergunta ou SQL canônico.
- A suíte externa Sakila de 30 itens permanece bloqueada para treino.
- A validação do treinamento é separada por família de SQL, não por linhas aleatórias.
- O corpus, hashes, parâmetros e métricas ficam no manifesto gerado; dados e adapters permaneccem ignorados pelo Git.

A exclusão automática detecta coincidência exata. A escolha das famílias foi também revisada para não reproduzir as intenções do benchmark; alterações futuras devem preservar ambas as proteções.

## Comandos sequenciais

Execute no PowerShell, na raiz \`C:\\Users\\Ceolin\\Documents\\code\\sqllm-speaker\`, com Docker Desktop iniciado:

~~~powershell
uv sync
uv run python -m unittest discover -s tests -t . -v
uv run python scripts/generate_pagila_specialization_corpus.py --label pagila-v18-fc7a867-pt-v1
~~~

O comando do gerador é bloqueado se o diretório de saída já existir. Para recriar deliberadamente um corpus novo, use outro rótulo e mantenha o manifesto anterior:

~~~powershell
uv run python scripts/generate_pagila_specialization_corpus.py --label pagila-v18-fc7a867-pt-v2
~~~

Faça primeiro o smoke test de dois passos. Ele valida CUDA, carga do adapter da fase 1, dados e escrita do novo artefato sem iniciar o treino completo:

~~~powershell
uv run python scripts/train_phase_02_pagila.py --run-name phase-02-pagila-smoke --max-train-samples 32 --max-validation-samples 8 --max-steps 2 --eval-steps 2 --save-steps 2
~~~

Com o smoke concluído, execute o treino comparável completo:

~~~powershell
uv run python scripts/train_phase_02_pagila.py --run-name phase-02-pagila-v1 --epochs 3 --eval-steps 20 --save-steps 20
~~~

O adapter final e \`run-manifest.json\` serão criados em:

~~~text
artifacts/runs/phase-02-pagila-v1-768f209d9ea8/
~~~

Não execute simultaneamente outro processo CUDA. Ao fim, o próximo passo obrigatório é repetir o benchmark interno Pagila e comparar o novo resultado contra \`artifacts/evaluations/phase-01-pagila-author-baseline/\`; não use perda de treino como evidência de melhora do autor SQL.
