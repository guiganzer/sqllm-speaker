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

Próximas implementações, nesta ordem:

1. Compilar contexto compacto de schema para cada consulta Pagila.
2. Ampliar a avaliação pública gerada e validada por execução.
3. Conectar o adapter treinado como autor SQL da sessão agentic.
4. Preparar especialização QLoRA com exemplos públicos gerados e executados no Pagila.
5. Comparar o adapter especializado, o adapter da fase 1 e o baseline no benchmark público congelado e na avaliação Pagila.

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
