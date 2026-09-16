# Entrada oficial da fase 2 privada

Use este procedimento antes do treino. Ele mantém o conteúdo privado em `data/raw/private/`, diretório ignorado pelo Git, e versiona apenas o contrato, a configuração de referência e manifestos redigidos.

## Materiais obrigatórios

1. `schema.sql`: DDL/base schema válido para o dialeto escolhido, sem linhas de dados e sem credenciais.
2. `queries.jsonl`: um objeto por linha com `pergunta` e `sql`. Os campos já existentes `id`, `categoria`, `dificuldade`, `dialeto` e `somente_leitura` são aceitos.
3. Dialeto confirmado. Para os materiais recebidos, o valor é `postgres`.
4. Contexto compacto de schema por consulta/endpoint. O DDL atual tem aproximadamente 619 KB e não pode ser entregue inteiro a um treino de 2.048 tokens; o limite inicial é 6.000 caracteres por exemplo.
5. Separação de finalidade: o conjunto inteiro não será usado em treino. O preparador cria `train`, `validation` e `test` determinísticos.

## Endpoints dinâmicos

Como `raw_*` e `vw_ep_*` são criadas no cadastro de endpoints, forneça também `endpoints.jsonl` quando qualquer consulta depender delas. Cada linha tem este contrato:

```json
{"endpoint_id":"identificador-estavel-nao-sensivel","schema_path":"snapshots/endpoint-a.sql"}
```

- `schema_path` é relativo à pasta do próprio manifest e não pode sair dela.
- Cada snapshot contém somente DDL do endpoint naquele momento.
- Consultas dinâmicas recebem o campo opcional `endpoint_id`; sem ele, usa-se o schema base.
- O preparador calcula um hash do snapshot e o inclui no exemplo privado. O conteúdo do DDL nunca é versionado.

O modelo deve receber esse snapshot em toda inferência. Treino não substitui introspecção em tempo de uso.

## Lacuna a concluir antes do primeiro treino

O preparador já rejeita contextos acima de 6.000 caracteres. Falta implementar o compilador de contexto que, para cada SQL validado, seleciona o DDL das tabelas referenciadas, expande dependências de `vw_ep_*` quando necessário e produz uma fatia compacta. Para isso, ainda precisamos da regra de cadastro dos endpoints ou de snapshots representativos de `raw_*` e `vw_ep_*`.

## Estrutura local

```text
data/raw/private/
  schema.sql
  queries.jsonl
  endpoints.jsonl                 # se houver endpoints dinâmicos
  snapshots/
    endpoint-a.sql
```

O arquivo `docs/templates/phase-02-endpoints.example.jsonl` é somente referência; não o copie com nomes de produção para o Git.

## Preparação

Após colocar os arquivos locais, execute a partir da raiz do repositório:

```powershell
uv run python scripts/prepare_phase_02.py `
  --queries data/raw/private/queries.jsonl `
  --base-schema data/raw/private/schema.sql `
  --endpoint-manifest data/raw/private/endpoints.jsonl `
  --dialect postgres `
  --output-label private-initial
```

Sem endpoints dinâmicos, omita `--endpoint-manifest`.

O comando cria, somente localmente:

- `data/processed/phase-02/<rotulo>-<hash>/train.jsonl`;
- `validation.jsonl` e `test.jsonl` isolados;
- `artifacts/reports/phase-02-intake-<rotulo>.json`, sem perguntas, SQL ou DDL.

Ele rejeita campos ausentes, exemplos não marcados como somente leitura, SQL fora da política, SQL inválido para o dialeto, endpoints desconhecidos, duplicatas e contextos grandes demais.

## Critério para liberar treino

Só iniciar o ajuste fino quando o relatório registrar partições não vazias, nenhum erro crítico de origem, dialeto confirmado, contextos compactos e snapshots para todos os endpoints dinâmicos usados em consultas. Com 500 exemplos, use o primeiro treino como especialização inicial; amplie a cobertura antes de declarar o resultado pronto para todos os objetos estáticos e dinâmicos.
