# Fase 2 — SFT agentic de português para SQL

Esta fase ocorre depois da fase 1 e ensina o protocolo de ferramentas: descobrir schema, propor SQL, reparar erro e finalizar em SQL, esclarecimento ou abstenção.

Fonte candidata: `Boakpe/pt-br-agentic-text-to-sql-distilled-trajectories` (7.442 trajetórias, Apache-2.0). Durante a preparação, `execute_sql` será convertido para `execute_readonly_sql` somente se passar na política local; trajetórias incompatíveis serão rejeitadas e contabilizadas.

O treino preservará mensagens `system`, `user`, `assistant` e `tool`, respeitando os JSON Schemas de `contracts.py`.

Antes de treinar: fixar revisão e checksum, remover ferramentas desconhecidas, filtrar SQL fora da política, redigir conteúdo sensível não pseudonimizado e criar avaliação agentic separada.

Métricas adicionais: chamadas JSON válidas, chamadas no estado correto, SQL bloqueado antes de execução, reparo bem-sucedido dentro de dois ciclos e finalização correta para ambiguidade/impossibilidade.
