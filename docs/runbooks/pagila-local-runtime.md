# Runtime local — Pagila em PostgreSQL 18

Este ambiente é exclusivamente local e isolado em Docker. O banco é publicado apenas em `127.0.0.1:54329`; não há acesso externo configurado.

## Estado criado

- Contêiner: `sqllm-pagila-postgres`
- Volume Docker: `sqllm-pagila-pgdata`
- Banco: `pagila`
- Imagem: PostgreSQL 18 Alpine, fixada no manifesto de dados.
- Fonte: Pagila na revisão `fc7a86771a7ff213597139942f1f57c36125d37d`.

A senha é aleatória e fica em um arquivo local ignorado pelo Git. Não a copie para documentação, commits ou mensagens.

## Operação

Inicie o Docker Desktop caso ainda não esteja ativo e execute, na raiz do projeto:

```powershell
docker start sqllm-pagila-postgres
docker exec sqllm-pagila-postgres pg_isready -U postgres -d pagila
```

Para abrir um cliente SQL dentro do próprio contêiner, sem revelar credencial:

```powershell
docker exec -it sqllm-pagila-postgres psql -U postgres -d pagila
```

Exemplo seguro de verificação:

```sql
SELECT count(*) FROM film;
SELECT count(*) FROM rental;
```

Para interromper preservando os dados no volume:

```powershell
docker stop sqllm-pagila-postgres
```

## Reconstrução controlada

A reconstrução destrói somente o ambiente Pagila local. Antes de fazê-la, confirme que o alvo é o contêiner e volume abaixo; nunca aplique comandos genéricos de remoção do Docker.

```powershell
docker rm -f sqllm-pagila-postgres
docker volume rm sqllm-pagila-pgdata
```

Em seguida, recrie o ambiente a partir dos arquivos e hashes documentados em [pagila-v18-fc7a867.md](../data-manifests/pagila-v18-fc7a867.md). O carregamento exige PostgreSQL 18 porque a revisão v18 usa recursos que não existem no PostgreSQL 16.
