# Manifesto de dados — Fase 1, SFT geral

## Origem

- Dataset: `emdemor/sql-create-context-pt`
- Revisão solicitada: `main`
- Revisão resolvida e fixada: `ee31747c93bdf859c57468ec1f28c4360cc84b1b`
- Data de aquisição: 2026-09-15T01:12:46Z
- Licença declarada: CC-BY-4.0
- Campos usados: `pergunta`, `contexto`, `resposta`

## Transformação

- normalização de quebras de linha e espaços da pergunta;
- validação de uma única statement SQL via SQLGlot;
- nenhuma tradução, truncamento ou alteração semântica do SQL/DDL;
- deduplicação pela combinação normalizada de pergunta, schema e SQL;
- separação determinística por hash de schema, com 10% dos grupos em validação;
- rejeição de qualquer campo acima de 16.000 caracteres.

## Resultado

| Medida | Valor |
|---|---:|
| Linhas de origem | 78.577 |
| Aceitas | 78.389 |
| Treino | 70.551 |
| Validação | 7.838 |
| Grupos de schema | 72.792 |
| Rejeitadas por SQL sem parse | 187 |
| Rejeitadas por tamanho | 1 |

Os arquivos locais estão em `data/raw/` e `data/processed/`, deliberadamente ignorados pelo Git. O relatório completo local está em `artifacts/reports/phase-01-data-ee31747c93bd.json`.
