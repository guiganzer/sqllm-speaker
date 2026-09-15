# ADR-001 — Estratégia de treinamento em três etapas

- **Status:** aprovada
- **Data:** 2026-09-14

## Contexto

O objetivo é responder perguntas em português com SQL ancorado no schema do banco do usuário. Treinar apenas no schema privado cria especialização, mas reduz a cobertura de linguagem e de construções SQL. Treinar apenas em dados genéricos não ensina as regras de negócio e os nomes reais do banco.

## Decisão

Adotar três etapas sequenciais:

1. SFT geral com dados públicos de Text-to-SQL em português, sempre incluindo DDL/schema no prompt.
2. SFT complementar com exemplos validados do schema próprio.
3. Inclusão do schema atual no prompt de inferência, com validação antes de qualquer execução.

## Consequências

- A etapa 1 torna o adapter fluente em SQL e na estrutura do problema.
- A etapa 2 melhora a precisão em nomes, relações e vocabulário do domínio real.
- A etapa 3 reduz o impacto de mudanças de schema e alucinação de tabelas/colunas.
- Cada etapa deve ter conjuntos de avaliação isolados e métricas registradas.

## Alternativas descartadas

- **Treinar um modelo do zero:** excede os recursos locais e não agrega valor proporcional.
- **Treinar somente no schema privado:** favorece overfitting e não cobre suficientemente a linguagem natural.
- **Não enviar o schema em inferência:** torna o sistema frágil quando o banco evolui.
