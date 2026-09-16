# SQLLM Speaker

Assistente local de **Text-to-SQL em português**. O projeto especializa um modelo aberto para transformar perguntas em português em SQL de leitura, sempre condicionado ao schema atual do banco e protegido por validações determinísticas.

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

## Arquitetura

```text
Pergunta em português + schema atual
                ↓
     Modelo especializado (LoRA/QLoRA)
                ↓
 Validador: sintaxe + schema + política SQL
                ↓
 Executor opcional com credencial somente leitura
                ↓
          Resultado ou impedimento seguro
```

A camada agentic é composta por contratos de ferramentas, política de leitura e uma máquina de estados determinística. O modelo nunca decide sozinho se uma consulta pode ser executada.

## Próxima etapa: banco de dados próprio

A fase 2 especializa o adapter no schema privado do usuário sem expor dados sensíveis ao Git. O roteiro completo, entregáveis e critérios de aceitação estão em [docs/roadmap/phase-02-private-schema.md](docs/roadmap/phase-02-private-schema.md).

Próximas implementações, nesta ordem:

1. Receber DDL/schema, dialeto e amostras de perguntas → SQL já validadas, sem credenciais nem dumps de produção.
2. Criar o snapshot normalizado e versionado por hash do schema, mantendo o conteúdo privado fora do Git.
3. Construir o dataset da fase 2 com divisão por schema/caso de uso e conjunto de avaliação isolado.
4. Executar QLoRA de especialização e registrar manifesto com modelo, dados, hiperparâmetros, seed e adapter.
5. Avaliar contra o benchmark público congelado e a avaliação privada, incluindo parse, schema, política, *exact match* e execução em ambiente seguro.
6. Conectar o runtime agentic a um perfilador de schema e executor real somente leitura, com reparo limitado e telemetria redigida.

Melhorias posteriores relevantes incluem cobertura de joins complexos, recuperação de contexto para schemas extensos, testes de regressão por dialeto, validação semântica com banco de homologação e uma interface de revisão humana antes de qualquer execução.

## Retomada rápida

Antes de alterar código, dados ou configuração, leia nesta ordem:

1. [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) — contexto mestre, escopo, regras e estado.
2. [ADR-001: estratégia de treinamento](docs/decisions/ADR-001-estrategia-de-treinamento.md).
3. [ADR-002: arquitetura agentic](docs/decisions/ADR-002-arquitetura-agentic.md).
4. [Arquitetura do runtime](docs/architecture/agentic-runtime.md).
5. [Roteiro da fase 2 privada](docs/roadmap/phase-02-private-schema.md).

## Desenvolvimento local

Pré-requisito: Python 3.11 e [uv](https://docs.astral.sh/uv/).

```powershell
uv sync
uv run python -m unittest discover -s tests -t . -v
```

O ambiente esperado é Windows com RTX 4070 Laptop de 8 GiB e 32 GiB de RAM. O alvo operacional inicial é um modelo de 4B parâmetros com QLoRA em 4-bit.

## Estrutura

- `configs/`: configurações versionadas e exemplos de execução.
- `data/`: dados locais por estágio; o conteúdo de datasets é ignorado pelo Git.
- `docs/`: decisões, manifestos, runbooks e roteiro de evolução.
- `scripts/`: preparação, treino e avaliação.
- `src/llm_to_sql/agentic/`: contratos de agentes, política SQL e máquina de estados.
- `tests/`: testes automatizados.
- `artifacts/`: adapters, métricas e relatórios gerados; não versionados.

## Segurança e dados

Não versione schemas privados, dados de clientes, dumps, credenciais, tokens do Hugging Face, adapters treinados ou artefatos de execução. O executor futuro deve usar uma conta dedicada somente leitura e aplicar limites de consulta, tempo e linhas retornadas.

A fonte de verdade para a continuidade do trabalho é [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md). O histórico Git contém as decisões e entregas anteriores; cada experimento deve acrescentar seu manifesto versionado.
