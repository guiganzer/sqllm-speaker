# Reparo SQL agentic limitado

## Objetivo

A camada runtime complementa o ajuste fino Pagila v2. Ela corrige uma falha de escopo ou uma falha de execução sem treinar novamente o modelo, e sem ampliar a autorização de banco.

## Fluxo

1. O especialista fornece relações candidatas.
2. O runtime compila somente seus schemas.
3. O autor v2 propõe uma única consulta SQL.
4. O guardião valida política e escopo.
5. Se houver falha de escopo ou de execução, o reparador recebe somente:
   - a pergunta original;
   - o mesmo schema permitido;
   - a SQL anterior;
   - o erro sanitizado.
6. É permitida somente uma nova proposta por padrão.
7. A política read-only, o limite de tempo e o limite de linhas são reaplicados.

Uma falha de política nunca é reparada automaticamente: ela bloqueia a sessão.

## Sessão local

Com Docker Desktop ativo, execute:

~~~powershell
uv run python scripts/run_pagila_model_agentic_session.py --question "Quais filmes PG têm descrições mais longas?" --tables film
~~~

Para uma pergunta relacional, informe todas e somente as relações necessárias:

~~~powershell
uv run python scripts/run_pagila_model_agentic_session.py --question "Quais atores participaram de filmes da categoria Action?" --tables actor,film_actor,film_category,category
~~~

A saída JSON registra cada proposta em generated_candidates, a quantidade de repairs, o estágio final e os resultados limitados. Para diagnóstico é possível ajustar max-repairs, porém não ultrapasse 1 no uso experimental padrão.

## Limites

Esta camada não sabe, por si só, se o resultado corresponde a uma intenção de negócio ambígua. O reparo resolve erro de banco ou escopo, não substitui validação humana, seleção de schema nem o benchmark congelado.
