# Manifesto de dados — Pagila público v18

## Identidade da fonte

| Campo | Valor |
| --- | --- |
| Base | Pagila, porta PostgreSQL do banco didático Sakila |
| Origem | https://github.com/xzilla/pagila |
| Revisão fixada | `fc7a86771a7ff213597139942f1f57c36125d37d` |
| Licença | PostgreSQL License; origem Sakila também documentada como BSD pela fonte |
| Dialeto de execução | PostgreSQL 18.6 |
| Imagem local | `postgres@sha256:d3e1620b530c944afa6e887d22eb899824da68e19c52024bf98f5220c88a65b2` |

## Integridade dos arquivos baixados

| Arquivo | SHA-256 |
| --- | --- |
| `pagila-schema.sql` | `e4fb54694cd89feb7604cc3c0d99773b95e57252035e199555a45353b9408caa` |
| `pagila-data.sql` | `eb0652bfcfc252989e6d4fb2b00a850ab453dc6ba4010c6855e6619dd8391370` |

A cópia local fica em `data/raw/pagila/fc7a86771a7ff213597139942f1f57c36125d37d/` e é ignorada pelo Git.

## Carga local validada

A carga executou `pagila-schema.sql` e `pagila-data.sql` com `ON_ERROR_STOP=1` em PostgreSQL 18.6. Verificações agregadas após a carga:

| Verificação | Resultado |
| --- | ---: |
| Tabelas no schema `public` | 23 |
| Filmes | 1.000 |
| Filmes com `description` | 1.000 |
| Clientes | 599 |
| Locações | 16.044 |

O runtime local, a porta e a credencial não são parte do manifesto. Consulte o runbook para iniciar/parar o contêiner sem expor a senha.

## Uso aprovado

Pagila é a base pública intermediária para:

- validar compilação de contexto de schema;
- gerar e executar consultas de leitura em português;
- medir segurança, referências de schema e execução;
- testar o runtime agentic público com contexto de schema e conta somente leitura.

Ele complementa o benchmark público congelado da fase 1 como a base de especialização e avaliação atual.
