# Plano — expansão multi-schema em cinco rodadas

## Objetivo

Melhorar o modelo atual sem trocar o modelo-base, treinando-o a receber **pergunta em português + subgrafo do schema + PKs/FKs** e devolver somente SQL correta. A expansão usa bases públicas reproduzíveis e preserva o benchmark geral congelado.

## Fontes e papéis

| Fonte | Papel |
| --- | --- |
| Fase 1 pública já processada | Replay geral contra esquecimento catastrófico |
| WikiSQL local | Fundação adicional de pergunta, tabela e SQL após normalização segura |
| Olist original | Domínio de e-commerce, joins reais e textos descritivos |
| Logistics Operations | Domínio logístico, métricas temporais e joins operacionais |
| Pagila | Benchmark especializado já existente; não reutilizar itens congelados |

O Olist original em CSV é canônico. A cópia SQLite é apenas o banco de execução rápida. O funil de marketing não é misturado ao catálogo Olist enquanto sua fonte original não estiver manifestada separadamente.

## Currículo relacional

Cada exemplo recebe apenas o subgrafo necessário:

| Tier | Proporção | Relações | Finalidade |
| --- | ---: | ---: | --- |
| `small` | 60% | 1–3 tabelas | seleção, filtro, agregação e joins básicos |
| `medium` | 25% | 4–5 tabelas | cadeias de FK, tempo, agrupamentos e outer joins |
| `heavy` | 15% | 6–8 tabelas | perguntas analíticas ponta a ponta realmente úteis |

Os packs versionados ficam em `configs/datasets/olist.json` e `configs/datasets/logistics.json`. Complexidade artificial é proibida: uma SQL pesada precisa responder a uma pergunta que justifique todas as relações usadas.

## Rodadas controladas

1. **Fundação normalizada:** WikiSQL convertido para o contrato do projeto e replay estratificado da fase 1.
2. **Relações pequenas:** packs `small` de Olist e Logistics com replay geral.
3. **Relações médias:** cadeias de FKs, datas, agrupamentos, zero ocorrências e `LEFT JOIN`.
4. **Relações pesadas:** packs `heavy`, exemplos contrastivos e reparos de erros observados.
5. **Consolidação:** mistura estratificada das quatro rodadas e replay geral ampliado.

Cada rodada inicia no último candidato aprovado. Um candidato reprovado não se torna base da rodada seguinte.

## Pipeline obrigatório por exemplo

```text
especificação da pergunta
        ↓
pack de relações mínimo
        ↓
SQL de referência revisada
        ↓
parse + política read-only + escopo do pack
        ↓
execução no banco + fingerprint do resultado
        ↓
separação por família/pack
        ↓
treino ou avaliação
```

O split não será aleatório por linha. Famílias, templates semânticos e paráfrases correlatas permanecem no mesmo split para impedir vazamento.

## Prompt especializado

O prompt `configs/prompts/sql-author-schema-fk-v1.json` exige:

- uma única SQL somente leitura;
- uso exclusivo de tabelas e colunas fornecidas;
- joins pelas relações `hard`;
- relações `soft` apenas quando necessárias e conforme suas observações;
- `LEFT JOIN` quando a pergunta pedir todos, inclusive entidades sem ocorrência;
- nenhuma explicação, Markdown ou filtro inventado.

## Barreiras e métricas

Cada saída mede, no mínimo:

- SQL presente e parseável;
- conformidade read-only;
- tabelas e colunas dentro do schema fornecido;
- execução aprovada;
- equivalência de resultado com o gabarito;
- exact match canônico;
- componentes estruturais: projeção, joins, predicados, agrupamento, ordenação e limite.

O benchmark geral congelado de 512 schemas permanece como gate de regressão. O candidato universal precisa preservar 100% de parse/política, pelo menos 98,05% de referências válidas e 64,06% de exact match canônico. Olist e Logistics terão holdouts próprios, separados por família e relation pack. Pagila continua sendo medido separadamente.

## Tarefas e estado

| # | Tarefa | Estado |
| ---: | --- | --- |
| 1 | Organizar as fontes locais em `data/raw/` | Concluída |
| 2 | Verificar os nove CSVs oficiais do Olist e registrar hashes | Concluída |
| 3 | Criar catálogos Olist e Logistics com PKs, FKs e packs | Concluída |
| 4 | Versionar o prompt schema+FK | Concluída |
| 5 | Criar validador read-only executável no SQLite Olist | Concluída |
| 6 | Criar ingestão reproduzível dos CSVs em PostgreSQL dedicado | Pendente |
| 7 | Criar parser seguro e normalizador do WikiSQL local, sem `eval` | Pendente |
| 8 | Criar especificações PT-BR e SQLs de referência na proporção 60/25/15 | Pendente |
| 9 | Validar em lote e gravar hashes/fingerprints dos resultados | Pendente |
| 10 | Congelar holdouts Olist e Logistics antes do treino | Pendente |
| 11 | Medir o prompt v1 sem novo treino | Pendente |
| 12 | Executar as cinco rodadas, com smoke e gates a cada rodada | Pendente |

## Próximo passo autorizado

Implementar a ingestão canônica de Olist e Logistics em um PostgreSQL local dedicado, incluindo DDL, tipos, PKs, FKs, contagens e testes de órfãos. Depois disso, o gerador de especificações poderá produzir e validar perguntas/SQLs sem depender da cópia SQLite de terceiros.
