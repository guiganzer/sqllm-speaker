# Manifesto — smoke WikiSQL criativo e retorno SQL

Data: 2026-09-17.

## Redação

- 10 itens WikiSQL de treino.
- 40 variantes PT-BR geradas pelo `Qwen3-4B-Instruct-2507`.
- 36 variantes aprovadas pelo contrato por candidato.
- 4 rejeições auditáveis: duas por pontuação final e duas por alteração do literal `Private/Presbyterian`.
- Todos os 10 itens preservaram ao menos duas variantes válidas.

## Primeira tentativa de retorno

As 36 variantes foram submetidas ao adapter `phase-01-general-e1-768f209d9ea8`. Todas produziram SQL parseável, permitida e restrita ao schema, mas nenhuma obteve exact match ou resultado equivalente.

O resultado não mede a capacidade do adapter: os jobs usaram por engano o contrato `sql-author-schema-fk-v1`, com `<dialeto>` e `<schema_e_relacionamentos>`. O adapter havia sido treinado e avaliado exclusivamente com `phase-01-general-v1`, formado pelo system prompt curto e pelos blocos `<schema>` e `<pergunta>`. As saídas mostraram o efeito sistemático da mudança de distribuição: filtros adicionais com valores inventados.

## Correção e decisão

O preparador de retorno passou a importar o construtor oficial do autor da fase 1 e grava `prompt_id=phase-01-general-v1` em cada job. O próprio construtor foi alinhado byte a byte ao espaçamento usado no corpus de treino. A primeira tentativa fica registrada como falha de integração e não como benchmark. Nenhuma geração em escala está autorizada até a repetição das 36 variantes sob o contrato correto.