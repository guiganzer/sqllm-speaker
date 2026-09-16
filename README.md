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

Próximas ações, nesta ordem:

1. Executar o smoke da v3 continuando o adapter v2.
2. Treinar por duas épocas com taxa de aprendizado reduzida.
3. Repetir as 24 perguntas congeladas sob o contrato básico de candidato único.
4. Comparar resultado executado e componentes SQL com a linha de base v2.

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


## Resultado da especialização Pagila v1

A primeira especialização Pagila foi concluída e medida no benchmark congelado: execução passou de 66,67% para 91,67%, resultados idênticos de 4,17% para 12,50% e exact match canônico de 0% para 4,17%. A conformidade de escopo caiu de 100% para 95,83%, por isso a próxima iteração ampliará o corpus relacional antes de qualquer uso autônomo. Consulte o [manifesto do experimento](docs/experiment-manifests/phase-02-pagila-v1-2026-09-16.md).


## Resultado Pagila v2

A especialização incremental v2 preservou 91,67% de SQL executado e aumentou equivalência de resultado para 20,83% (5/24), contra 12,50% da v1 e 4,17% antes da especialização. O runtime agentic e suas barreiras de segurança permanecem obrigatórios. Veja o [manifesto v2](docs/experiment-manifests/phase-02-pagila-v2-2026-09-16.md).


## Pagila v3 preparada

A iteração v3 permanece no modelo atual e ataca o gargalo semântico. Foram geradas 2.066 perguntas PT-BR em 40 famílias, com 795 SQLs distintas validadas no Pagila somente leitura. O schema fornecido ao treino passa a incluir PK, FK, cardinalidade e hints categóricos públicos controlados. O runtime também ganhou geração de múltiplos candidatos e ranking determinístico, mantendo escopo, política e reparo limitado.

O baseline por componentes mostra onde medir o ganho: projeção 29,17%, ordenação 25%, joins 50% e agrupamento 54,17%. Consulte o [runbook da v3](docs/runbooks/phase-03-pagila-v3.md) para os comandos de smoke, treino e avaliação, e o [manifesto do corpus](docs/data-manifests/pagila-v3-corpus-2026-09-16.md) para hashes e isolamento.

## Treino Pagila v3 concluído

O adapter v3 concluiu duas épocas e 198 passos com perda final de validação 0,203507 e 59/59 testes aprovados. A curva permaneceu estável e monotonicamente melhor, mas a promoção depende do benchmark congelado de 24 perguntas. Veja o [manifesto do treino v3](docs/experiment-manifests/phase-03-pagila-v3-2026-09-16.md).

## Avaliação v3: ganho especializado, regressão geral

A v3 melhorou o Pagila: 24/24 em parse/escopo, 22/24 executadas e 8/24 resultados idênticos, contra 5/24 na v2. Porém, no benchmark geral de 512 schemas, conformidade ao schema caiu de 98,05% para 88,67% e exact match de 64,06% para 46,09%. Por isso, a v3 não foi promovida como adapter universal. A próxima iteração deve introduzir replay geral estratificado e atacar joins/projeções restantes. Veja a [avaliação completa](docs/experiment-manifests/phase-03-pagila-v3-evaluation-2026-09-16.md).