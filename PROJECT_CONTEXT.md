# Contexto mestre do projeto

Este é o documento de salvaguarda do projeto. Uma nova pessoa, máquina ou agente deve lê-lo antes de trabalhar no repositório. Ele descreve a intenção, as escolhas confirmadas, o estado atual e como continuar.

## Objetivo

Construir um assistente local de **Text-to-SQL** que receba uma pergunta em português e o schema atual de um banco de dados, e responda somente com SQL correto para aquele schema.

O produto final deve favorecer consultas de leitura. A geração de SQL não é, por si só, autorização para executar comandos que alterem dados.

## Escopo confirmado

O projeto seguirá três etapas públicas:

1. **Treinamento geral:** ensinar SQL e a conversão pergunta em português + schema para SQL com dados públicos.
2. **Experimento Pagila:** especializar e avaliar com um banco PostgreSQL público, reproduzível e descritivo.
3. **Schema em tempo de uso:** enviar ao modelo apenas o schema Pagila relevante a cada pergunta, evitando depender apenas do que foi memorizado no treinamento.

O trabalho evoluiu da fase 1 para o runtime agentic e o experimento público Pagila.

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
- Dumps locais, credenciais, modelos baixados e adapters não entram no Git.
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
| `emdemor/sql-create-context-pt` | Fonte principal da etapa 1 | Revisão `ee31747c93bdf859c57468ec1f28c4360cc84b1b` adquirida: 78.389 pares aceitos após validação. Licença CC-BY-4.0. |
| `Boakpe/bird-sql-portuguese` | Complemento complexo | Tradução PT de BIRD, com perguntas, evidências e SQL. Requer obter e associar os schemas originais do BIRD; o visualizador do Hub apresenta erro de configuração. |
| `Boakpe/pt-br-agentic-text-to-sql-distilled-trajectories` | Etapa posterior opcional | 7.442 trajetórias PT-BR de uso de ferramentas. Não misturar no primeiro treino de resposta SQL direta. |

Não combinar `b-mc2/sql-create-context` com `emdemor/sql-create-context-pt`, pois o segundo é sua tradução e duplicaria os exemplos.

## Estado atual — 15 de setembro de 2026

- Repositório Git inicializado na branch `main` e espelhado publicamente em https://github.com/guiganzer/sqllm-speaker.
- Estrutura de pastas, documentação e configuração-exemplo criadas.
- A base determinística do runtime agentic foi criada em `src/llm_to_sql/agentic/`, com testes padrão do Python criados em `tests/`.
- Projeto uv configurado com Python 3.11 fixado em `.python-version`, dependências em `.venv` e lockfile `uv.lock`.
- Os 27 testes automatizados passam via `uv run python -m unittest discover -s tests -t . -v`.
- O dataset da fase 1 foi preparado localmente: 78.577 linhas de origem, 78.389 aceitas, 70.551 em treino e 7.838 em validação. Foram rejeitadas 187 consultas que não fizeram parse e 1 exemplo acima do limite de caracteres.
- A GPU passou no preflight PyTorch: RTX 4070 Laptop, CUDA 12.8, BF16 e 8 GiB de VRAM. Dependências de QLoRA/SFT foram adicionadas ao `.venv` e fixadas pelo `uv.lock`.
- O smoke test QLoRA da fase 1 foi aprovado na GPU: 5 passos em 43,112 s, perda de treino 1,6972 e perda de validação 0,4041. O adapter local e o manifesto ignorado pelo Git estão em `artifacts/runs/phase-01-smoke-768f209d9ea8/`; o resumo versionado está em `docs/experiment-manifests/phase-01-smoke-2026-09-15.md`.
- A fase 1 foi concluída: uma época completa em 70.550 exemplos, 4.410 passos e 10h15m. A perda final de validação foi 0,0468. O benchmark isolado de 512 schemas registrou 100% de parse, saída SQL e política de leitura; 98,05% de referências ao schema válidas; e 64,06% de *exact match* canônico. O modelo-base, nas mesmas condições, obteve 0% por produzir raciocínio em vez de SQL. Consulte `docs/experiment-manifests/phase-01-general-e1-2026-09-15.md`.
- A calibração de 100 passos foi aprovada: 0,110 passo/s e 1,766 amostra/s. Para uma época completa, a estimativa é de aproximadamente 11h20; reservar uma janela de 12 horas. Consulte `docs/experiment-manifests/phase-01-calibration-2026-09-15.md`.
- Experimento público Pagila/Sakila carregado localmente em PostgreSQL 18.6: 23 tabelas, 1.000 filmes com descrição, 599 clientes e 16.044 locações. A fonte e hashes estão em `docs/data-manifests/pagila-v18-fc7a867.md`; a operação local está em `docs/runbooks/pagila-local-runtime.md`. O runtime agentic está conectado por ferramentas de perfil/schema/executor com conta `sqllm_readonly`, descritas em `docs/runbooks/pagila-agentic-session.md`; a avaliação pública programática contém 24 consultas executadas. Próxima implementação: compilador de contexto compacto. O conjunto público de 512 schemas continuará imutável como benchmark de regressão. O modelo-base está no cache local e a revisão foi fixada em `768f209d9ea81521153ed38c47d515654e938aea`.

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
