# ADR-001 — Estratégia pública de treinamento e validação

- **Status:** aprovada
- **Data:** 2026-09-15

## Contexto

O projeto precisa responder perguntas em português com SQL ancorado no schema ativo e manter execução segura. A fase geral já ensina linguagem e SQL; o próximo experimento deve usar uma base relacional pública, reproduzível e com dados descritivos para validar especialização, contexto de schema e runtime agentic.

## Decisão

Adotar três etapas públicas e sequenciais:

1. SFT geral com dados públicos de Text-to-SQL em português, sempre incluindo DDL/schema no prompt.
2. Especialização e avaliação no Pagila, banco PostgreSQL público com dados de filmes, descrições, relações, views e transações.
3. Inclusão do schema Pagila relevante no prompt de inferência, com validação de política e execução somente leitura.

## Consequências

- A etapa 1 torna o adapter fluente em SQL e na estrutura do problema.
- A etapa 2 mede aderência a relações, nomes e consultas reais em uma fonte pública reproduzível.
- A etapa 3 reduz alucinação de tabelas/colunas e limita a execução por código e permissões do banco.
- Cada etapa mantém conjuntos de avaliação isolados e manifestos com versão, licença, hashes e métricas.

## Alternativas descartadas

- **Treinar um modelo do zero:** excede os recursos locais e não agrega valor proporcional.
- **Usar somente respostas sem schema em contexto:** torna o sistema frágil para relações, views e mudanças de estrutura.
- **Executar SQL sem política e conta de leitura:** não atende ao requisito de segurança do runtime.
