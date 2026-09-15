# Contexto mestre do projeto

Este é o documento de salvaguarda do projeto. Uma nova pessoa, máquina ou agente deve lê-lo antes de trabalhar no repositório. Ele descreve a intenção, as escolhas confirmadas, o estado atual e como continuar.

## Objetivo

Construir um assistente local de **Text-to-SQL** que receba uma pergunta em português e o schema atual de um banco de dados, e responda somente com SQL correto para aquele schema.

O produto final deve favorecer consultas de leitura. A geração de SQL não é, por si só, autorização para executar comandos que alterem dados.

## Escopo confirmado

O projeto seguirá três etapas:

1. **Treinamento geral:** ensinar SQL e a conversão pergunta em português + schema para SQL com dados públicos.
2. **Especialização no schema próprio:** aplicar ajuste fino adicional em perguntas e SQL validados para o banco do usuário.
3. **Schema em tempo de uso:** enviar ao modelo o schema atual a cada pergunta, evitando depender apenas do que foi memorizado no treinamento.

O trabalho iniciado neste repositório evoluiu para a base agentic e o planejamento da etapa 1.

## Decisão agentic

O projeto será um sistema agentic, não um único prompt que gera SQL. Um mesmo modelo local atua em papéis especializados, cada um com ferramentas e contexto mínimos. A política de segurança e as transições de estado são código determinístico, nunca decisões deixadas ao modelo.

O baseline selecionado para avaliação é `Boakpe/Qwen3-4B-Thinking-2507-Text-to-SQL-Agent-FT`, modelo Apache-2.0 de 4B parâmetros especializado em PT-BR, tool use e Text-to-SQL. Ele é adequado como referência pela VRAM disponível. O modelo do projeto será um adapter próprio, treinado a partir de um modelo-base compatível e comparado contra esse baseline; não haverá dependência funcional do checkpoint externo.

Fontes da decisão:

- https://huggingface.co/Boakpe/Qwen3-4B-Thinking-2507-Text-to-SQL-Agent-FT
- https://huggingface.co/datasets/Boakpe/pt-br-agentic-text-to-sql-distilled-trajectories

## Princípios inegociáveis

- O schema é contexto obrigatório tanto no treino quanto na inferência.
- A resposta do modelo deve conter SQL, sem explicações, quando a solicitação for respondível.
- O executor deve operar com credencial somente de leitura e impor uma lista de comandos permitidos. Começar com `SELECT`, `WITH` e `EXPLAIN`; nunca executar SQL gerado diretamente em produção sem validação.
- Dados privados, dumps, credenciais, modelos baixados e adapters não entram no Git.
- Toda origem de dados deve ter versão/revisão, licença e transformação registradas.
- O conjunto de avaliação nunca pode ser reutilizado no treino.

## Arquitetura-alvo

```text
Pergunta em português
        + schema atual / metadados permitidos
        ↓
Modelo especializado (adapter LoRA/QLoRA)
        ↓
Validador de sintaxe, schema e política de segurança
        ↓
Executor com acesso somente de leitura (opcional)
        ↓
Resultado ou mensagem de impedimento
```

## Ambiente conhecido

- Sistema: Windows.
- CPU: Intel Core i9-14900HX (24 núcleos / 32 threads).
- GPU: NVIDIA RTX 4070 Laptop com 8 GB de VRAM.
- Memória: 32 GB.
- Espaço livre inicial em `C:`: aproximadamente 806 GB.

Implicação: o alvo local é ajuste fino QLoRA em 4-bit. Para o fluxo agentic, 4B é o alvo operacional inicial porque deixa VRAM para contexto e reparos; 7B será experimento posterior. Treinar um LLM do zero está fora do escopo.

## Dados candidatos já pesquisados

| Dataset | Papel | Observação |
|---|---|---|
| `emdemor/sql-create-context-pt` | Fonte principal da etapa 1 | 78.577 pares em português: `pergunta`, `contexto` (DDL) e `resposta` (SQL). Licença CC-BY-4.0. |
| `Boakpe/bird-sql-portuguese` | Complemento complexo | Tradução PT de BIRD, com perguntas, evidências e SQL. Requer obter e associar os schemas originais do BIRD; o visualizador do Hub apresenta erro de configuração. |
| `Boakpe/pt-br-agentic-text-to-sql-distilled-trajectories` | Etapa posterior opcional | 7.442 trajetórias PT-BR de uso de ferramentas. Não misturar no primeiro treino de resposta SQL direta. |

Não combinar `b-mc2/sql-create-context` com `emdemor/sql-create-context-pt`, pois o segundo é sua tradução e duplicaria os exemplos.

## Estado atual — 14 de setembro de 2026

- Repositório Git inicializado na branch `main`.
- Estrutura de pastas, documentação e configuração-exemplo criadas.
- A base determinística do runtime agentic foi criada em `src/llm_to_sql/agentic/`, com testes padrão do Python criados em `tests/`.
- A execução dos testes está pendente: em 2026-09-14, `python` apontou para o atalho da Microsoft Store e não há interpretador disponível. Não instalar sem autorização explícita.
- Não há dependências externas instaladas, datasets locais, tokens, modelos ou experimentos ainda.
- Próxima atividade: implementar o pipeline de obtenção, checagem e preparação dos dados da fase 1; em paralelo, preservar a interface de ferramentas definida para o treinamento agentic posterior.

## Como retomar em outra máquina

1. Clone o repositório e leia este arquivo, `README.md` e os documentos em `docs/`.
2. Verifique a GPU, VRAM, drivers e espaço em disco; ajuste a configuração, nunca os dados de avaliação.
3. Crie ambiente Python isolado e instale dependências somente quando o plano da fase correspondente for aprovado.
4. Baixe datasets em `data/raw/`, mantendo a revisão do Hub em um manifesto versionado.
5. Gere dados limpos em `data/processed/` e outputs em `artifacts/`; ambos são ignorados pelo Git.
6. Registre decisões novas em `docs/decisions/` e atualize a seção **Estado atual** deste arquivo.

## Convenções de trabalho

- Código e comentários técnicos podem estar em inglês; documentação e interface devem permanecer em português do Brasil.
- Não sobrescrever arquivos nem descartar alterações locais sem inspeção e autorização explícita.
- Antes de um treino, registrar modelo-base, hash/revisão dos dados, hiperparâmetros, seed, métricas e local do adapter.
