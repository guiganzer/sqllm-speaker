# Manifesto de dados — expansão pública Text-to-SQL

Data de inventário: 17 de setembro de 2026.

Os arquivos brutos permanecem em `data/raw/` e são ignorados pelo Git. Este manifesto registra origem, licença, volume e fingerprint; transformações futuras terão manifestos próprios.

## WikiSQL

- Fonte: https://www.kaggle.com/datasets/thedevastator/dataset-for-developing-natural-language-interfac
- Licença declarada: CC0 1.0 / domínio público.
- Diretório: `data/raw/kaggle__thedevastator__wikisql/`
- Estrutura local: `phase`, `question`, `table`, `sql`.
- Fingerprint do conjunto: `f0df7e7af51c01490b6a7f33f0997f78cfd5babb668934d82cd75e4355691575`.

| Split original | Linhas | SHA-256 |
| --- | ---: | --- |
| `train.csv` | 56.355 | `40ab934b90321494ce56b2727f98cfefac4111c4883d7b4a8c8b7d0eb8956fef` |
| `validation.csv` | 8.421 | `8467d63b06f4d353747c4454c79ba05753852594521f4d4919de2a2e2af30d09` |
| `test.csv` | 15.878 | `f3b2b35d99218d4f4c082d4daa3bc9305db2b5bcde6d93d1c3215877ef945076` |

Total: 80.654 exemplos. O campo `table` e o campo `sql` desta exportação estão serializados como estruturas Python/numpy. O normalizador deve usar parser seguro e validadores explícitos; `eval` é proibido. Os splits originais serão preservados e nenhuma linha de validação/teste será incluída no treino.

## Logistics Operations Database

- Fonte: https://www.kaggle.com/datasets/yogape/logistics-operations-database
- Licença declarada: MIT.
- Natureza: base sintética de operações logísticas de 2022 a 2024.
- Diretório: `data/raw/kaggle__yogape__logistics-operations/`
- Estrutura: 14 tabelas CSV e `DATABASE_SCHEMA.txt`.
- Total local: 549.706 linhas de dados.
- Fingerprint do conjunto: `960360f214fa8aa48a973a22c3d127666a43daedfe1eafa5434c62eba23409f5`.
- Catálogo versionado: `configs/datasets/logistics.json`.

As contagens locais diferem de números aproximados mostrados em algumas descrições públicas. O projeto usa os arquivos locais e seus hashes como versão efetiva, não estimativas da página.

## Olist

O inventário detalhado, hashes, chaves e relações do Olist estão em `docs/data-manifests/olist-original-2026-09-17.md`.

## Definição do fingerprint

Para WikiSQL e Logistics, o fingerprint é SHA-256 da concatenação ordenada de `nome_do_arquivo + sha256_do_arquivo`. Ele identifica exatamente o conjunto local sem versionar os dados brutos.

## Condições para uso no treino

1. Parse seguro e determinístico da fonte.
2. Registro da transformação e do código que a produziu.
3. SQL parseável no dialeto de destino.
4. Schema mínimo explícito e relation pack registrado.
5. Execução somente leitura bem-sucedida quando houver banco correspondente.
6. Separação por família semântica, schema e template, evitando vazamento entre splits.
7. Bloqueio explícito de benchmarks congelados.
