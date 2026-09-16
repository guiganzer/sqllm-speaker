# SQLLM Speaker

Assistente local e agentic de **Text-to-SQL em português**. O projeto especializa um modelo aberto para transformar perguntas em português em SQL de leitura, sempre condicionado ao schema atual do Pagila e protegido por validações determinísticas.

> SQL gerado não é autorização de execução. O runtime aceita somente consultas de leitura após validação de sintaxe, referências ao schema e política de segurança.

## Estado do projeto

A fase 1 — treinamento geral com dados públicos — está concluída. O adapter QLoRA foi treinado por uma época sobre 70.550 exemplos e avaliado em 512 schemas isolados, que permanecem congelados como benchmark de regressão.

| Métrica do benchmark da fase 1 | Resultado |
| --- | ---: |
| Saída SQL e parse válido | 100% |
| Conformidade com política de leitura | 100% |
| Referências válidas ao schema | 98,05% |
| *Exact match* SQL canônico | 64,06% |

O *exact match* é deliberadamente rígido: compara a estrutura canônica com a consulta de referência. SQL semanticamente equivalente pode não pontuar nessa métrica; por isso, as métricas de schema, segurança e execução também fazem parte da avaliação.

## Arquitetura agentic

```text
Pergunta em português + schema Pagila relevante
                ↓
  Orquestrador → especialista de schema → autor SQL
                ↓
 Guardião de política → executor somente leitura → finalizador
                ↓
          Resultado, bloqueio ou reparo limitado
```

A política e as transições são código determinístico. O runtime Pagila obtém perfil e múltiplos schemas, bloqueia escrita, limita tempo/linhas e executa com a conta `sqllm_readonly`. Consulte a [sessão agentic](docs/runbooks/pagila-agentic-session.md).

## Próxima etapa: experimento público Pagila

O Pagila está carregado localmente em PostgreSQL 18 e validado com 23 tabelas, 1.000 filmes descritivos e 16.044 locações. Consulte o [manifesto](docs/data-manifests/pagila-v18-fc7a867.md), o [runtime local](docs/runbooks/pagila-local-runtime.md), a [avaliação pública](docs/runbooks/pagila-public-evaluation.md) e o [estudo de candidatos](docs/research/public-descriptive-databases.md).

O compilador de contexto já está disponível em [pagila-context-compiler.md](docs/runbooks/pagila-context-compiler.md): ele fornece somente as relações usadas na consulta e recusa ultrapassar o orçamento do prompt. O adapter da fase 1 já atua como autor SQL na [sessão modelada](docs/runbooks/pagila-model-agentic-session.md), com guardião de escopo, política e executor somente leitura.

A qualidade pré-especialização foi congelada e repetida no [benchmark do autor SQL](docs/runbooks/pagila-author-benchmark.md): 24/24 propostas passaram no parse/escopo/política, 16/24 executaram, 1/24 devolveu o resultado de referência e 0/24 teve *exact match* canônico. A repetição independente produziu os mesmos resultados.

A validação externa de terceiros foi adicionada em [external-sakila-validation.md](docs/runbooks/external-sakila-validation.md): os 30 gabaritos MIT do Sakila foram transpostos de MySQL para PostgreSQL/Pagila e todos executaram sob a conta somente leitura. Ela é bloqueada para treino e não substitui a métrica PT-BR do Pagila.

Próximas implementações, nesta ordem:

1. Gerar um corpus público Pagila de especialização, separado das 24 perguntas congeladas do benchmark.
2. Validar por execução, deduplicar e registrar o manifesto desse corpus.
3. Treinar o adapter QLoRA Pagila e repetir o benchmark com o mesmo contrato.
4. Exibir os deltas com o comparador versionado e, só então, evoluir a seleção autônoma de relações pelo especialista de schema.

## Retomada rápida

Antes de alterar código, dados ou configuração, leia nesta ordem:

1. [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) — contexto mestre, escopo, regras e estado.
2. [ADR-001: estratégia de treinamento](docs/decisions/ADR-001-estrategia-de-treinamento.md).
3. [ADR-002: arquitetura agentic](docs/decisions/ADR-002-arquitetura-agentic.md).
4. [Arquitetura do runtime](docs/architecture/agentic-runtime.md).
5. [Manifesto Pagila](docs/data-manifests/pagila-v18-fc7a867.md).

## Desenvolvimento local

Pré-requisito: Python 3.11 e [uv](https://docs.astral.sh/uv/).

```powershell
uv sync
uv run python -m unittest discover -s tests -t . -v
```

Para executar a avaliação pública ou a sessão agentic, inicie o Docker Desktop e siga os runbooks Pagila.

## Estrutura

- `configs/`: configurações versionadas e exemplos de execução.
- `data/`: fontes e saídas locais; conteúdo de datasets é ignorado pelo Git.
- `docs/`: decisões, manifestos, runbooks e pesquisa.
- `scripts/`: preparação, treino, avaliação e sessões locais.
- `src/llm_to_sql/agentic/`: contratos de agentes, política SQL, ferramentas e máquina de estados.
- `tests/`: testes automatizados.
- `artifacts/`: adapters, métricas e relatórios gerados; não versionados.

## Segurança e dados

Não versione credenciais, tokens, modelos baixados, adapters treinados, resultados de consultas ou artefatos de execução. O executor usa uma conta dedicada somente leitura e aplica limites de consulta, tempo e linhas retornadas.

A fonte de verdade para a continuidade do trabalho é [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md). O histórico Git contém as decisões e entregas anteriores; cada experimento deve acrescentar seu manifesto versionado.


## Treinamento de especialização Pagila

A fase 2 está implementada e pronta para execução controlada. O corpus é gerado publicamente, validado por execução e separado dos benchmarks Pagila e Sakila. O treino continua o adapter da fase 1 em vez de criar um adapter do zero. Siga os comandos e critérios de continuidade no [runbook da fase 2](docs/runbooks/phase-02-pagila-specialization.md).
