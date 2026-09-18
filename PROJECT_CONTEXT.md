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

## Estado atual — 16 de setembro de 2026

- Repositório Git inicializado na branch `main` e espelhado publicamente em https://github.com/guiganzer/sqllm-speaker.
- Estrutura de pastas, documentação e configuração-exemplo criadas.
- A base determinística do runtime agentic foi criada em `src/llm_to_sql/agentic/`, com testes padrão do Python criados em `tests/`.
- Projeto uv configurado com Python 3.11 fixado em `.python-version`, dependências em `.venv` e lockfile `uv.lock`.
- Os 59 testes automatizados passam via `uv run python -m unittest discover -s tests -t . -v`.
- O dataset da fase 1 foi preparado localmente: 78.577 linhas de origem, 78.389 aceitas, 70.551 em treino e 7.838 em validação. Foram rejeitadas 187 consultas que não fizeram parse e 1 exemplo acima do limite de caracteres.
- A GPU passou no preflight PyTorch: RTX 4070 Laptop, CUDA 12.8, BF16 e 8 GiB de VRAM. Dependências de QLoRA/SFT foram adicionadas ao `.venv` e fixadas pelo `uv.lock`.
- O smoke test QLoRA da fase 1 foi aprovado na GPU: 5 passos em 43,112 s, perda de treino 1,6972 e perda de validação 0,4041. O adapter local e o manifesto ignorado pelo Git estão em `artifacts/runs/phase-01-smoke-768f209d9ea8/`; o resumo versionado está em `docs/experiment-manifests/phase-01-smoke-2026-09-15.md`.
- A fase 1 foi concluída: uma época completa em 70.550 exemplos, 4.410 passos e 10h15m. A perda final de validação foi 0,0468. O benchmark isolado de 512 schemas registrou 100% de parse, saída SQL e política de leitura; 98,05% de referências ao schema válidas; e 64,06% de *exact match* canônico. O modelo-base, nas mesmas condições, obteve 0% por produzir raciocínio em vez de SQL. Consulte `docs/experiment-manifests/phase-01-general-e1-2026-09-15.md`.
- A calibração de 100 passos foi aprovada: 0,110 passo/s e 1,766 amostra/s. Para uma época completa, a estimativa é de aproximadamente 11h20; reservar uma janela de 12 horas. Consulte `docs/experiment-manifests/phase-01-calibration-2026-09-15.md`.
- Experimento público Pagila/Sakila carregado localmente em PostgreSQL 18.6: 23 tabelas, 1.000 filmes com descrição, 599 clientes e 16.044 locações. A fonte e hashes estão em `docs/data-manifests/pagila-v18-fc7a867.md`; a operação local está em `docs/runbooks/pagila-local-runtime.md`. O runtime agentic opera com perfil/schema/executor sob a conta `sqllm_readonly`. O adapter da fase 1 foi integrado como autor SQL com contexto compacto e guardião de escopo; consulte `docs/runbooks/pagila-model-agentic-session.md`. O baseline público do autor SQL (24 perguntas) foi concluído e repetido com resultados idênticos: 100% parse/escopo/política, 66,67% execução, 4,17% resultado idêntico e 0% *exact match*. O contrato e o comparador pós-especialização estão em `docs/runbooks/pagila-author-benchmark.md`; suas 24 perguntas ficam excluídas do treino. A validação externa MIT `text2sql-benchmark-id` também foi fixada na revisão `fab6e4d40da5f58dd42fe5072a01ca6305835d88`: seus 30 itens Sakila foram derivados para PostgreSQL/Pagila, com 30/30 execuções aceitas, e estão bloqueados para treino. Consulte `docs/runbooks/external-sakila-validation.md`. Próxima implementação: corpus público Pagila separado, validado e documentado para especialização QLoRA. O conjunto público de 512 schemas continuará imutável como benchmark de regressão. O modelo-base está no cache local e a revisão foi fixada em `768f209d9ea81521153ed38c47d515654e938aea`.

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


## Estado da fase 2 — especialização Pagila

A implementação da fase 2 está pronta para execução local: o gerador parametrizado em scripts/generate_pagila_specialization_corpus.py cria um corpus público em português, valida cada SQL no PostgreSQL Pagila sob sqllm_readonly, compila apenas o schema relevante e grava hashes em um manifesto. O treino está em scripts/train_phase_02_pagila.py e continua o adapter concluído da fase 1, sem reinicializar LoRA. As 24 perguntas Pagila congeladas e os 30 itens externos Sakila permanecem proibidos no treino; a divisão de validação é por família de SQL. Execute e retome pelo runbook docs/runbooks/phase-02-pagila-specialization.md.


## Resultado fase 2 Pagila v1 — 16 de setembro de 2026

A especialização QLoRA Pagila v1 foi concluída a partir do adapter geral da fase 1: 119 exemplos de treino, 30 validações, três épocas e 24 passos. O mesmo benchmark Pagila congelado mostrou 22/24 SQLs executados contra 16/24 antes; resultados idênticos passaram de 1/24 para 3/24 e exact match canônico de 0/24 para 1/24. Parse/escopo caiu de 24/24 para 23/24. O resultado é uma melhoria material de execução, mas não aprova uso autônomo: a próxima iteração deve ampliar o corpus público em estruturas relacionais sem alterar benchmarks. Consulte docs/experiment-manifests/phase-02-pagila-v1-2026-09-16.md.


## Preparação fase 2 Pagila v2 — 16 de setembro de 2026

O corpus incremental v2 foi preparado e validado no Pagila público: 212 exemplos, 165 em treino e 47 em validação; fingerprint 71ae988b0fefdb4f7a149d743ff6cc463e63eacf23dd916e955beec9e84f4e94. Ele continua a v1 com famílias de joins explícitos e externos, aliases, ordenação, limites e views, mantendo o benchmark interno e a suíte Sakila fora do treino. O smoke e o treino estão documentados em docs/runbooks/phase-02-pagila-v2.md.


## Resultado fase 2 Pagila v2 — 16 de setembro de 2026

A v2 continuou o adapter Pagila v1 com 212 exemplos públicos validados (165 treino, 47 validação). No benchmark congelado, preservou 22/24 SQLs executados e elevou resultados idênticos de 3/24 para 5/24. Parse e escopo permanecem em 23/24. Ela é o candidato ativo para inferência experimental, ainda protegido pelo runtime agentic; a próxima melhoria deve focar reparo orientado por execução e geração estruturada. Consulte docs/experiment-manifests/phase-02-pagila-v2-2026-09-16.md.


## Runtime de reparo agentic — 16 de setembro de 2026

Após a especialização v2, o runtime ganhou um reparo estruturado limitado: falhas de escopo e de execução podem receber uma única nova proposta com a SQL anterior, erro sanitizado e exatamente o mesmo schema. Falhas de política continuam bloqueadas. O adapter experimental padrão da sessão Pagila é phase-02-pagila-v2-768f209d9ea8. A implementação tem cobertura na suíte de 59 testes e o uso está em docs/runbooks/pagila-agentic-repair.md.


## Preparação Pagila v3 — 16 de setembro de 2026

A v3 mantém o modelo Qwen/Qwen3-4B-Thinking-2507 e continua o adapter v2; comparação entre modelos foi adiada. O corpus oficial tem 2.066 perguntas PT-BR, 1.579 exemplos de treino, 487 de validação, 40 famílias e 795 SQLs únicas executadas sob sqllm_readonly. O fingerprint é 3a4a4b93d6f6638ee5576945b60cddb84bc557e0f7ab55b6bf39f4bcb794a7c7. O contexto pagila-enriched-v1 inclui PK, FK, cardinalidade e hints categóricos de lista pública permitida, preservando o contexto antigo para reproduzir v1/v2. O runtime agora aceita beam search de até cinco candidatos e ranking semântico determinístico; todas as barreiras anteriores continuam ativas.

A linha de base estrutural da v2 nas 24 perguntas é: relações e agregações 95,83%; limite 87,50%; predicados 75%; agrupamento 54,17%; joins 50%; projeção 29,17%; ordenação 25%. Assim, o objetivo explícito da v3 é melhorar estrutura semântica, e não apenas perda de validação. Arquivos locais, comandos de treino e critérios estão em docs/runbooks/phase-03-pagila-v3.md; o manifesto versionado está em docs/data-manifests/pagila-v3-corpus-2026-09-16.md. O smoke v3 foi concluído e aprovado: 64 exemplos de treino, 32 de validação, 2 passos, perda de treino 0,153642 e perda de validação 0,287430, sem OOM ou descarte. O treino integral de duas épocas está liberado, mas ainda não foi iniciado. Consulte docs/experiment-manifests/phase-03-pagila-v3-smoke-2026-09-16.md.

## Resultado do treino Pagila v3 — 16 de setembro de 2026

O treino v3 foi concluído a partir do adapter v2: 1.579 exemplos de treino, 487 de validação por famílias, duas épocas e 198 passos. A perda média de treino foi 0,010463 e a perda final de validação 0,203507. A curva de validação melhorou de 0,222756 no passo 50 para 0,203507 no passo 198, sem reversão ou instabilidade; 59/59 testes passaram. O adapter phase-03-pagila-v3-768f209d9ea8 está tecnicamente liberado para o benchmark congelado, mas não promovido. Consulte docs/experiment-manifests/phase-03-pagila-v3-2026-09-16.md.

## Avaliação Pagila v3 e regressão geral — 16 de setembro de 2026

No benchmark Pagila congelado, a v3 passou de 23/24 para 24/24 em parse/escopo, preservou 22/24 execuções, elevou resultados idênticos de 5/24 para 8/24 e exact match de 1/24 para 2/24. Agrupamento melhorou de 13/24 para 17/24 e ordenação de 6/24 para 11/24; joins caiu de 12/24 para 9/24 e projeção de 7/24 para 5/24.

O benchmark geral congelado de 512 schemas revelou regressão material: referências válidas ao schema caíram de 502/512 (98,05%) para 454/512 (88,67%) e exact match de 328/512 (64,06%) para 236/512 (46,09%). Parse, saída SQL e política permaneceram em 100%. Assim, a v3 é candidata especializada Pagila, não substituta universal; o padrão permanece v2 e o adapter geral da fase 1 é preservado. A próxima iteração precisa de replay geral estratificado e exemplos direcionados aos erros restantes. Consulte docs/experiment-manifests/phase-03-pagila-v3-evaluation-2026-09-16.md.
## Expansão pública multi-schema — 17 de setembro de 2026

Após a regressão geral observada na v3, a estratégia confirmada é enriquecer o modelo atual com replay geral e bases públicas multi-schema, sem comparar ou trocar o modelo-base nesta fase. As fontes locais são WikiSQL (80.654 exemplos, CC0), Olist original (nove CSVs, CC BY-NC-SA 4.0) e Logistics Operations (14 tabelas, MIT). Os dados brutos permanecem ignorados pelo Git; proveniência e fingerprints estão em `docs/data-manifests/public-sql-expansion-2026-09-17.md` e `docs/data-manifests/olist-original-2026-09-17.md`.

Olist e Logistics possuem catálogos versionados em `configs/datasets/`, com PKs, FKs e relation packs distribuídos em 60% small, 25% medium e 15% heavy. O prompt `configs/prompts/sql-author-schema-fk-v1.json` limita o autor ao schema fornecido. `scripts/validate_schema_sql.py` renderiza o prompt e valida/executa SQL no espelho SQLite Olist com política read-only, escopo do pack, limite de linhas e limite de instruções. O teste real de `orders-payments` executou com sucesso e a suíte completa passou com 66/66 testes.

O plano aprovado prevê cinco rodadas controladas com replay geral. A próxima implementação é a ingestão reproduzível de Olist e Logistics em PostgreSQL, seguida pelo normalizador seguro do WikiSQL, criação de SQLs de referência, congelamento de holdouts e só então treino. Consulte `docs/plans/public-schema-sql-five-rounds.md`.
## Pipeline criativo WikiSQL — 17 de setembro de 2026

WikiSQL permanece como fonte principal da primeira rodada. Para evitar traduções literais pobres ou criatividade semanticamente incorreta, o pipeline foi dividido em cinco responsabilidades: parser AST restrito sem `eval`; plano semântico e execução determinísticos; redator com quatro variantes PT-BR; retorno de cada pergunta para SQL pelo adapter geral; e crítico que escolhe apenas entre candidatos aprovados por estrutura ou resultado executado.

O redator e o crítico usam `Qwen/Qwen3-4B-Instruct-2507` não pensante, revisão `cdbee75f17c01a7cc42f958dc650907174af0554`. O retorno usa `Qwen/Qwen3-4B-Thinking-2507` com `phase-01-general-e1-768f209d9ea8`. A amostra inicial planejada é de 6.000 itens de treino, 1.000 de validação e 1.000 de teste, selecionados por hash estável. O runner grava um item por vez e retoma por ID. O gate do redator preserva candidatos válidos individualmente e exige ao menos duas variantes aprovadas por item; toda rejeição fica auditável.

O smoke do planejador validou 15/15 referências. Um teste deliberado com resposta Thinking truncada foi rejeitado e registrado, confirmando que saída sem JSON não avança. A suíte completa possui 75 testes aprovados. Nenhum treino deve começar até o corpus final ter 100% de `training_ready`, separação de splits, hashes, retorno aprovado e replay geral. Operação: `docs/runbooks/wikisql-creative-pt-pipeline.md`.

O corpus Olist reservado para a rodada 2 foi gerado e validado separadamente: 120 exemplos PT-BR, sendo 72 small, 30 medium e 18 heavy; 89 ficaram em treino e 31 em validação por famílias. Ele não entra na rodada WikiSQL. Manifesto: docs/data-manifests/olist-public-pt-v1-2026-09-17.md.
