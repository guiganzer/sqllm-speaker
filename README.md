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

Base agentic e pipeline da fase 1 implementados. O projeto usa Python 3.11, `uv`, ambiente `.venv` e uma RTX 4070 Laptop de 8 GiB para QLoRA em 4-bit.

- Dataset geral preparado: 70.551 exemplos de treino e 7.838 de validação, isolados por schema.
- Smoke test QLoRA aprovado; detalhes em [docs/experiment-manifests/phase-01-smoke-2026-09-15.md](docs/experiment-manifests/phase-01-smoke-2026-09-15.md).
- Treino completo retomável e benchmark estrutural por geração estão disponíveis nos runbooks.
- A fonte de verdade do estado é [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md).

Para validar a base local:

```powershell
uv run python -m unittest discover -s tests -t . -v
```
