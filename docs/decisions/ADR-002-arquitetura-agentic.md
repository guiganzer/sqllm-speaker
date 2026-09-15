# ADR-002 — Runtime agentic e modelo de referência

- **Status:** aprovada
- **Data:** 2026-09-14

## Decisão

Usar um único modelo local em seis papéis: orquestrador, especialista de schema, autor de SQL, guardião de política, reparador e finalizador. Segurança e transições de estado são determinísticas.

As únicas ferramentas iniciais são `get_database_profile`, `get_table_schema` e `execute_readonly_sql`. A execução aceita exclusivamente SQL que passe na política local de leitura.

O checkpoint `Boakpe/Qwen3-4B-Thinking-2507-Text-to-SQL-Agent-FT` é o baseline de avaliação. É um modelo Apache-2.0 de 4B, especializado em PT-BR para schema, execução exploratória e reparo. Seu dataset público tem 7.442 trajetórias agentic em PT-BR e mesma licença. Fontes: https://huggingface.co/Boakpe/Qwen3-4B-Thinking-2507-Text-to-SQL-Agent-FT e https://huggingface.co/datasets/Boakpe/pt-br-agentic-text-to-sql-distilled-trajectories.

O adapter próprio priorizará uma base de 4B com template de chat e tool calling compatíveis. Isso é mais apropriado que 7B no notebook, pois libera VRAM para contexto, reparos e treino QLoRA. Um modelo 7B poderá ser comparado posteriormente.

## Consequências

- Papéis não são múltiplos modelos carregados simultaneamente.
- O guardião rejeita escrita, múltiplas statements e SQL fora da política antes da execução.
- Erros sanitizados vão apenas ao reparador e há no máximo dois reparos.
- As ferramentas do treino devem obedecer exatamente aos contratos do runtime.
- Métricas externas do checkpoint são somente referência; o projeto executará seus próprios benchmarks.
