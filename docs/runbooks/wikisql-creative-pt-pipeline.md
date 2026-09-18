# Runbook — WikiSQL PT-BR criativo e semanticamente validado

## Decisão

O WikiSQL continua sendo a fonte principal da primeira rodada. A tradução não será feita em uma única chamada. O pipeline separa criatividade de correção:

```text
WikiSQL estruturado
  → plano semântico determinístico + execução da referência
  → redator Instruct gera 4 perguntas PT-BR
  → adapter Text-to-SQL converte cada pergunta de volta para SQL
  → comparação por schema, política, exact match e resultado executado
  → crítico Instruct escolhe a pergunta mais natural entre as aprovadas
  → corpus final mantém a SQL original validada
```

O redator e o crítico usam `Qwen/Qwen3-4B-Instruct-2507`, variante oficial não pensante, fixada na revisão `cdbee75f17c01a7cc42f958dc650907174af0554`. O teste de retorno usa o modelo Thinking com o adapter geral aprovado da fase 1. Assim, o mesmo modelo não inventa a pergunta e aprova sozinho sua própria invenção.

O contrato do redator é aplicado por candidato. Variantes inválidas são registradas individualmente e descartadas; um item só segue se conservar pelo menos duas perguntas válidas para comparação. Isso evita perder três boas variantes por um único erro de pontuação ou de literal sem relaxar nenhum gate semântico.

## Escala inicial

A primeira execução seleciona deterministicamente 8.000 itens:

- 6.000 do treino original;
- 1.000 da validação original;
- 1.000 do teste original.

Os splits originais são preservados. Teste e validação não entram no treino. Cada item produz quatro candidatos, portanto o teste de retorno pode criar até 32.000 gerações SQL.

## 1. Preparar planos e jobs do redator

```powershell
uv run python scripts/prepare_wikisql_creative_jobs.py `
  --sample-plan train=6000,validation=1000,test=1000 `
  --output-dir data/interim/wikisql-creative-v1/writer-jobs
```

Essa etapa interpreta o repr numpy com AST restrita, nunca `eval`, executa cada SQL de referência em SQLite e cria o plano semântico.

## 2. Gerar quatro perguntas por item

O primeiro comando baixa o modelo Instruct caso ele ainda não esteja no cache. Execute um split por vez. O arquivo é incremental: repetir o comando continua dos IDs restantes.

```powershell
uv run python scripts/run_local_generation_jobs.py `
  --jobs data/interim/wikisql-creative-v1/writer-jobs/train.jsonl `
  --output data/interim/wikisql-creative-v1/writer-responses/train.jsonl `
  --max-jobs 500 `
  --max-new-tokens 384 `
  --temperature 0.7 `
  --top-p 0.8
```

Repita até aparecer `Nenhum job pendente`. Depois execute o mesmo para `validation` e `test`, alterando os dois caminhos.

## 3. Criar jobs de retorno pergunta-para-SQL

```powershell
uv run python scripts/prepare_wikisql_roundtrip_jobs.py `
  --writer-jobs data/interim/wikisql-creative-v1/writer-jobs/train.jsonl `
  --writer-responses data/interim/wikisql-creative-v1/writer-responses/train.jsonl `
  --output data/interim/wikisql-creative-v1/roundtrip-jobs/train.jsonl
```

## 4. Gerar a SQL de retorno

```powershell
uv run python scripts/run_local_generation_jobs.py `
  --jobs data/interim/wikisql-creative-v1/roundtrip-jobs/train.jsonl `
  --output data/interim/wikisql-creative-v1/roundtrip-responses/train.jsonl `
  --model-id Qwen/Qwen3-4B-Thinking-2507 `
  --model-revision 768f209d9ea81521153ed38c47d515654e938aea `
  --adapter artifacts/runs/phase-01-general-e1-768f209d9ea8 `
  --max-jobs 1000 `
  --max-new-tokens 192 `
  --temperature 0
```

Repita até concluir e depois processe os outros splits.

## 5. Avaliar o retorno

```powershell
uv run python scripts/evaluate_wikisql_roundtrip.py `
  --roundtrip-jobs data/interim/wikisql-creative-v1/roundtrip-jobs/train.jsonl `
  --roundtrip-responses data/interim/wikisql-creative-v1/roundtrip-responses/train.jsonl `
  --output data/interim/wikisql-creative-v1/roundtrip-evaluations/train.jsonl
```

Um candidato só avança se respeitar política e schema e tiver exact match ou resultado não vazio equivalente à referência.

## 6. Preparar e executar o crítico

```powershell
uv run python scripts/prepare_wikisql_critic_jobs.py `
  --writer-jobs data/interim/wikisql-creative-v1/writer-jobs/train.jsonl `
  --roundtrip-evaluations data/interim/wikisql-creative-v1/roundtrip-evaluations/train.jsonl `
  --output data/interim/wikisql-creative-v1/critic-jobs/train.jsonl

uv run python scripts/run_local_generation_jobs.py `
  --jobs data/interim/wikisql-creative-v1/critic-jobs/train.jsonl `
  --output data/interim/wikisql-creative-v1/critic-responses/train.jsonl `
  --max-jobs 500 `
  --max-new-tokens 192 `
  --temperature 0
```

## 7. Finalizar o split

```powershell
uv run python scripts/finalize_wikisql_creative_corpus.py `
  --critic-jobs data/interim/wikisql-creative-v1/critic-jobs/train.jsonl `
  --critic-responses data/interim/wikisql-creative-v1/critic-responses/train.jsonl `
  --output data/processed/phase-04/wikisql-creative-pt-v1/train.jsonl
```

Repita as etapas 3 a 7 para `validation` e `test`. Somente `train.jsonl` e `validation.jsonl` serão usados pelo treinador. `test.jsonl` será congelado como avaliação.

## Gates antes do treino

- nenhum registro com `training_ready=false`;
- 100% com referência executada;
- 100% com retorno aprovado;
- zero IDs compartilhados entre splits;
- hashes e contagens registrados em manifesto;
- mistura com replay geral preparada e validada;
- smoke QLoRA concluído antes do treino integral.

O comando de treino integral só será liberado depois desses gates; gerar arquivos não equivale a autorizar treinamento.
