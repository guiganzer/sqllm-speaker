# Manifesto de dados — Olist original

Data de verificação: 17 de setembro de 2026.

## Decisão de origem

A fonte canônica é o dataset **Brazilian E-Commerce Public Dataset by Olist**, distribuído pela organização Olist no Kaggle sob licença CC BY-NC-SA 4.0. Ele contém nove CSVs e aproximadamente 100 mil pedidos entre 2016 e 2018.

- Fonte: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
- Diretório local ignorado pelo Git: `data/raw/brazilian-ecommerce-public-dataset-olist/`
- Catálogo versionado: `configs/datasets/olist.json`
- Espelho SQLite auxiliar: `data/raw/kaggle__terencicp__olist-sqlite/olist.sqlite`

Os CSVs originais são preservados byte a byte. As aspas fazem parte do formato CSV e não devem ser removidas: avaliações e outros textos podem conter vírgulas, aspas e quebras de linha.

## Inventário verificado

| Arquivo | Linhas de dados | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| `olist_customers_dataset.csv` | 99.441 | 9.033.957 | `983a422239e1712ded753b3bf9ecf47dc73f144d306029dcfa99e70a226883d2` |
| `olist_geolocation_dataset.csv` | 1.000.163 | 61.273.883 | `b514f6fc991b9566aeba02aa5d67e2c3630f034b60a0e05aa0d082a3b66d88d6` |
| `olist_order_items_dataset.csv` | 112.650 | 15.438.671 | `0bc4d068c4fe38cbb01bd90e8746e3c613fe7b4baef75fab7b0e329701c3e279` |
| `olist_order_payments_dataset.csv` | 103.886 | 5.777.138 | `4f713964f2815dbbaa40b9488268c55aac3627bfce5aa96cf58d1f3616de3cc0` |
| `olist_order_reviews_dataset.csv` | 99.224 | 14.451.670 | `012b61c7593e34f51fa614efdf802b9c7056ce6aae5307ddb93236e7cfc797d7` |
| `olist_orders_dataset.csv` | 99.441 | 17.654.914 | `8df58ef3d2d7e9944010f7beecd9b75367f5588ec6e3c91cec19ae3345ef9ecf` |
| `olist_products_dataset.csv` | 32.951 | 2.379.446 | `3e6569628a17fbc75fd206ee357b59e20364b9afa90f5b6cd5b4d624c58aa9cc` |
| `olist_sellers_dataset.csv` | 3.095 | 174.703 | `1f643d2b950373b85735e7794b20986f528d7a000432e7c6f9bcbb44d0846a0e` |
| `product_category_name_translation.csv` | 71 | 2.613 | `a81f0d1f27b27e7293f761bc79e3ce8f348ee39c4b3ed3e49bde38f478586278` |

O espelho `olist.sqlite` tem 112.701.440 bytes e SHA-256 `49446afd935721ee12fc95316fbee9666a3e1bd4872dfa194fe4625d6762a81a`. As contagens das nove tabelas equivalentes coincidem com os CSVs.

## Chaves e relações

As relações duras foram verificadas sem órfãos no espelho SQLite:

- `orders.customer_id -> customers.customer_id`;
- `order_items.order_id -> orders.order_id`;
- `order_items.product_id -> products.product_id`;
- `order_items.seller_id -> sellers.seller_id`;
- `order_payments.order_id -> orders.order_id`;
- `order_reviews.order_id -> orders.order_id`.

Três relações exigem tratamento explícito e são marcadas como `soft`:

- categoria de produto para tradução: existem categorias nulas ou sem tradução;
- CEP de cliente para geolocalização;
- CEP de vendedor para geolocalização.

`geolocation_zip_code_prefix` não é único. Qualquer consulta geográfica deve agregar ou deduplicar `geolocation` antes do join para impedir multiplicação artificial de linhas.

## Isolamento do funil de marketing

O SQLite auxiliar contém `leads_qualified` e `leads_closed`, mas essas tabelas pertencem ao dataset separado **Marketing Funnel by Olist**. Elas não entram no catálogo canônico de e-commerce. Só serão adicionadas a um catálogo separado após aquisição e manifesto próprios.

## Uso permitido no projeto

- Os CSVs são a fonte de verdade para ingestão e auditoria.
- O SQLite serve para desenvolvimento e validação read-only imediata.
- Perguntas e SQLs de treino serão geradas em arquivos processados separados.
- Exemplos reservados para avaliação nunca poderão reaparecer no treino, nem como paráfrases.
