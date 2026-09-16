# Benchmark do autor SQL — Pagila

Este benchmark congela a qualidade do **autor SQL** antes da especialização Pagila. Ele usa 24 perguntas públicas programáticas e SQLs de referência executados no Pagila 18.6. O conjunto não é material de treino.

## Contrato de medição

Para isolar a capacidade de autoria SQL, as relações candidatas são extraídas da SQL de referência. Portanto, o benchmark mede geração, compatibilidade estrutural e execução; ele **não** mede o especialista que escolhe tabelas a partir da pergunta.

Cada caso usa:

- a mesma pergunta em português;
- o mesmo conjunto de relações candidatas e DDL compacto;
- geração determinística com 128 novos tokens;
- guardião de escopo, política somente leitura e execução com `sqllm_readonly`;
- comparação estrita do resultado em ordem e conteúdo, além de *exact match* SQL canônico.

O fingerprint do conjunto é `2cdd251a51a650307e055c6c42ff04cd29c5a3c811a8a0e3e5fd8da79c6c1b10`.

## Baseline pré-especialização

| Métrica | Resultado |
| --- | ---: |
| Perguntas avaliadas | 24/24 |
| Parse e relações no escopo | 24/24 (100%) |
| SQL aceito pela política | 24/24 (100%) |
| Execução concluída | 16/24 (66,67%) |
| Resultado igual à referência | 1/24 (4,17%) |
| *Exact match* canônico | 0/24 (0%) |

O adapter geral sabe obedecer ao contrato SQL, mas ainda não conhece bem o vocabulário, as colunas e as relações do Pagila. Esse é o baseline que justifica uma especialização pública, não uma conclusão sobre a capacidade final do projeto.

## Gerar ou retomar

Os resultados ficam em `artifacts/evaluations/`, ignorados pelo Git. O comando processa quatro casos por vez e persiste cada previsão; repita com `--resume` até `complete: true`.

```powershell
uv run python scripts/evaluate_pagila_phase_01_author.py `
  --label phase-01-pagila-author-baseline `
  --resume
```

## Comparação após especialização

Depois de treinar um adapter Pagila, execute o mesmo benchmark com novo label e o caminho do novo adapter, mantendo `--max-new-tokens 128` e `--max-context-characters 6000`.

```powershell
uv run python scripts/evaluate_pagila_phase_01_author.py `
  --adapter-path artifacts/runs/<adapter-pagila> `
  --label pagila-specialized-e1 `
  --resume

uv run python scripts/compare_pagila_author_evaluations.py `
  --baseline artifacts/evaluations/phase-01-pagila-author-baseline/report.json `
  --candidate artifacts/evaluations/pagila-specialized-e1/report.json
```

O comparador recusa relatórios incompletos ou com fingerprint, total de exemplos ou parâmetros de geração diferentes. A tabela de deltas é a comparação de conclusão entre os adapters.