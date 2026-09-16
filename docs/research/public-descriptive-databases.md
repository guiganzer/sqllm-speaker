# Estudo — bases públicas com dados descritivos

## Decisão de trabalho

**Recomendação imediata: Pagila**, a porta PostgreSQL do banco clássico Sakila. Ele é o melhor próximo experimento controlado: é relacional, possui carga de dados pronta, usa PostgreSQL como os materiais anteriores e contém relações textuais/descritivas úteis — especialmente `film.title`, `film.description`, categorias, atores, clientes e transações de locação.

A recomendação define o caminho atual do projeto: validar o compilador de contexto, o runtime somente leitura e a avaliação em um schema público, fixo e reproduzível.

## Critérios usados

- Dados e schema públicos, com licença e origem identificáveis.
- Banco relacional já modelado, não apenas CSV ou JSON solto.
- Conteúdo textual/descritivo consultável.
- Relações suficientes para filtros, joins, agregações, ordenação, views e busca textual.
- Carga local compatível com PostgreSQL e com a máquina disponível.
- Complexidade de ingestão proporcional ao objetivo de Text-to-SQL.

## Comparativo

| Candidato | Pontos fortes | Limitações | Veredito |
| --- | --- | --- | --- |
| **Pagila / Sakila** | PostgreSQL pronto; schema, dados e instruções de carga; filmes com `description`; relações de clientes, estoque, pagamentos e locações; views e recursos de busca textual. | Escala moderada: é uma base didática, não um corpus massivo de texto. Não traz pares pergunta→SQL em português prontos. | **Usar agora**. |
| Stack Exchange Data Dump | Dados relacionais muito grandes e textos longos em perguntas, respostas, títulos e tags; schema do dump documentado. | Importação XML e normalização próprias; licença CC BY-SA por conteúdo; precisa escolher um site/recorte e controlar tamanho. | Segunda fase, para volume textual. |
| Open Library | Metadados bibliográficos e descrições muito ricos; dumps mensais amplos. | Fornecido como TSV/JSON, não como banco pronto; carga relacional e modelagem próprias; dumps de obras e edições têm múltiplos GB. | Pesquisa futura, não é o primeiro experimento. |
| AdventureWorks | Banco de negócio maduro, histórico e com documentação oficial; inclui produtos e descrições. | SQL Server/T-SQL em vez de PostgreSQL; menos alinhado ao runtime PostgreSQL pretendido. | Alternativa se houver interesse em T-SQL. |

## Fonte e licença da recomendação

O repositório Pagila fornece `pagila-schema.sql` e `pagila-data.sql`, instruções de carga com `psql`, e declara a licença PostgreSQL; sua origem Sakila também é descrita com licença BSD. O schema expõe a coluna `description` da tabela `film`.

- https://github.com/xzilla/pagila
- https://github.com/xzilla/pagila/blob/master/pagila-schema.sql

Para os candidatos futuros:

- https://meta.stackexchange.com/questions/2677/database-schema-documentation-for-the-public-data-dump-and-sede
- https://openlibrary.org/developers/dumps
- https://github.com/Microsoft/sql-server-samples/tree/master/samples/databases/adventure-works

## Escopo do experimento Pagila

1. Fixar o commit/release do Pagila e registrar hash de `pagila-schema.sql` e `pagila-data.sql` em um manifesto.
2. Carregar o banco em PostgreSQL local sem alterar a fonte original.
3. Gerar snapshot do schema e contexto compacto por consulta, respeitando o orçamento do modelo.
4. Construir uma suíte de perguntas em português e SQL de leitura **gerada e validada por execução**, sem redigir manualmente centenas de pares.
5. Reservar teste isolado e medir parse, referências ao schema, política somente leitura, *exact match* e execução.
6. Só depois avaliar se o corpus textual maior do Stack Exchange justifica uma segunda base.

## Limite importante

Uma base de dados com descrições não produz sozinha pares de treinamento Text-to-SQL. O conteúdo dos registros serve para executar e validar consultas; os pares pergunta→SQL precisam vir de uma fonte licenciada ou de geração programática com validação estrutural e por execução. O adapter da fase 1 já cobre o aprendizado geral de português→SQL; Pagila será usado para especialização/evaluação de schema e runtime.
