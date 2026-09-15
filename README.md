# LLM para SQL em português

Projeto para especializar um modelo aberto que converte perguntas em português em SQL seguro e fundamentado no schema fornecido.

## Retomada rápida

Antes de alterar código ou dados, leia nesta ordem:

1. [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) — estado, escopo, arquitetura e regras do projeto.
2. [docs/decisions/ADR-001-estrategia-de-treinamento.md](docs/decisions/ADR-001-estrategia-de-treinamento.md) — decisão dos três estágios.
3. [docs/decisions/ADR-002-arquitetura-agentic.md](docs/decisions/ADR-002-arquitetura-agentic.md) — arquitetura agentic e escolha de modelo.
4. [docs/architecture/agentic-runtime.md](docs/architecture/agentic-runtime.md) — agentes, ferramentas e fluxo.
5. [docs/training/phase-01-general-sft.md](docs/training/phase-01-general-sft.md) — plano de treino geral.

## Estrutura

- `configs/`: configurações versionadas e exemplos de execução.
- `data/`: dados locais, separados por estágio; o conteúdo dos datasets não vai ao Git.
- `docs/`: documentação, decisões e planos reprodutíveis.
- `scripts/`: automações de preparação, treino e avaliação.
- `src/llm_to_sql/agentic/`: contratos de agentes, política SQL e máquina de estados do runtime.
- `tests/`: testes automatizados.
- `artifacts/`: adapters, métricas e relatórios gerados; não versionados.

## Estado

Base agentic — implementada, com suíte de testes criada. A execução dos testes aguarda um Python 3.11+ instalado. Ainda não há dados baixados, dependências instaladas ou treinamento executado.
