# Fase 1 — SFT geral de português para SQL

## Resultado esperado

Produzir um adapter QLoRA local que receba um schema em DDL e uma pergunta em português, retornando exclusivamente uma consulta SQL. Esta fase ensina a habilidade geral; ela não conhece, nem deve conhecer, o banco privado do usuário.

## Fonte e recorte inicial

Fonte primária: `emdemor/sql-create-context-pt`, fixada por revisão do Hugging Face antes de qualquer download.

Campos de origem:

- `pergunta`: pergunta em português;
- `contexto`: uma ou mais instruções `CREATE TABLE`;
- `resposta`: SQL de referência.

O dataset contém 78.577 linhas e é a tradução em português de `b-mc2/sql-create-context`. Não importar sua versão inglesa, para evitar duplicação. A licença declarada é CC-BY-4.0; preservar atribuição e a revisão usada no manifesto.

O complemento BIRD em português fica fora da primeira execução. Ele será incorporado apenas depois de o pipeline tratar schemas originais, `evidence` e o erro atual de configuração do dataset no Hub.

## Formato canônico de treino

Cada registro limpo deve ser convertido para uma conversa de três mensagens:

```text
system: Você é um assistente especializado em SQL. Gere somente uma consulta SQL compatível com o schema fornecido. Não explique a resposta.
user: <schema>
{DDL do contexto}
</schema>

<pergunta>
{pergunta em português}
</pergunta>
assistant: {SQL de referência}
```

Não traduzir nomes de tabelas, colunas, valores literais ou dialeto SQL. Apenas o texto natural da pergunta é português.

## Pipeline planejado

1. **Manifesto de origem** — registrar ID, revisão imutável, licença, data de obtenção, campos e checksum dos arquivos recebidos.
2. **Aquisição** — baixar para `data/raw/` sem versionar os arquivos no Git.
3. **Normalização** — remover espaços redundantes, padronizar quebras de linha e manter o SQL sem reescrita semântica.
4. **Filtragem estrutural** — excluir registros sem pergunta, DDL ou SQL; rejeitar SQL que não faça parse e exemplos acima do limite conservador de 16.000 caracteres. A filtragem por tokens do tokenizer escolhido ocorrerá antes do treino.
5. **Deduplicação** — usar hash de `DDL + pergunta + SQL` normalizados e manter relatório de linhas removidas.
6. **Divisão de dados** — separar treino/validação por grupo de schema, nunca por linha aleatória. Um mesmo DDL não deve aparecer nos dois conjuntos.
7. **Serialização** — gerar JSONL de treino e validação no formato canônico e um relatório de estatísticas.
8. **Treino** — executar QLoRA com logs, seed e hiperparâmetros registrados.
9. **Avaliação** — medir parse de SQL, referências a tabelas/colunas existentes e conformidade de saída; não usar a validação para treinamento.

## Configuração inicial proposta

Consulte [configs/phase-01-general-sft.example.yaml](../../configs/phase-01-general-sft.example.yaml). Ela é um ponto de partida, não uma execução aprovada. A escolha exata do modelo-base será validada em um teste de VRAM antes do treino completo.

## Critérios de aceite antes de treinar

- Manifesto de origem e licença presentes.
- Nenhum registro vazio ou SQL sintaticamente inválido no conjunto aceito.
- Nenhuma chave de deduplicação compartilhada entre treino e validação.
- Relatório com contagem, distribuição de tokens e exemplos rejeitados.
- Formato do prompt testado em pelo menos cinco registros, preservando DDL e SQL.

## Métricas de sucesso da fase

- Taxa de SQL sintaticamente válido na validação.
- Taxa de tabelas e colunas referenciadas que existem no DDL fornecido.
- Taxa de respostas que contêm somente SQL, sem prosa ou blocos Markdown.
- Avaliação humana cega de uma amostra estratificada por complexidade.

Não usar apenas *exact match*: consultas SQL semanticamente equivalentes podem ter texto diferente.

## Próxima implementação autorizada

Criar o pipeline de aquisição e preparação do `emdemor/sql-create-context-pt`, com manifesto e testes de qualidade. Não baixar modelos ou iniciar treinamento até concluir e revisar o relatório de dados processados.
