# Fase 2 — especialização com schema privado

Este roteiro converte o objetivo de usar um banco de dados próprio em uma sequência segura, reprodutível e mensurável. Ele não autoriza acesso a produção nem o envio de dados privados ao repositório.

## Resultado esperado

Um adapter QLoRA especializado no domínio do banco do usuário, integrado ao runtime agentic para produzir SQL de leitura em português e validado em exemplos privados que nunca participam do treino.

## Entradas necessárias do usuário

Antes de iniciar o processamento, reunir em canal seguro:

- DDL ou export do schema sem dados sensíveis, com dialeto e versão do banco.
- Descrição funcional de tabelas, colunas ambíguas, chaves e relacionamentos importantes.
- Perguntas em português e SQL correspondente já validado por alguém que conheça o domínio.
- Regras de negócio relevantes, consultas proibidas, papéis de acesso e limite aceitável de linhas/tempo.
- Ambiente de homologação ou cópia minimizada para avaliar execução; nunca credenciais de produção no repositório.

## Contrato de privacidade

- Schema, exemplos, resultados, conexões e artefatos privados ficam sob `data/private/` e `artifacts/`, ambos ignorados pelo Git.
- Apenas manifests redigidos podem ser versionados: hashes, contagens, dialeto, versões, métricas agregadas e decisões.
- Tokens e credenciais devem vir de variáveis de ambiente ou cofre de segredos; não entram em arquivos de configuração versionados.
- Um snapshot de schema recebe identificador por hash para detectar mudanças sem publicar seu conteúdo.

## Plano de implementação

### 1. Perfil e snapshot do schema

Implementar um adaptador de introspecção por dialeto que obtenha tabelas, colunas, tipos, chaves e comentários permitidos. Normalizar em uma representação estável, calcular hash e produzir um perfil redigido. Critério: o snapshot de mesma estrutura gera o mesmo hash e nunca inclui valores de linhas.

### 2. Compilação de contexto e preparação do dataset privado

Criar um compilador que reduza cada snapshot ao DDL relevante para a consulta, expanda dependências de views e respeite o orçamento de contexto. Em seguida, validar SQL com `sqlglot`, associar cada pergunta ao snapshot correto e rejeitar duplicatas, comandos de escrita e referências inexistentes. Separar treino, validação e teste por schema/caso de uso para impedir vazamento. Critério: relatório com contagens, rejeições e hashes, sem conteúdo privado versionado.

### 3. Treino de especialização

Adicionar uma configuração de fase 2 baseada no adapter da fase 1. Registrar modelo-base, commit do código, versão/hash dos dados, dialeto, seed, hiperparâmetros, custo e localização privada do adapter. Critério: execução retomável e manifesto final reproduzível.

### 4. Avaliação em camadas

Executar, em conjuntos nunca vistos no treino:

1. parse e SQL único;
2. referências válidas ao schema;
3. política somente leitura;
4. *exact match* canônico;
5. execução em homologação com limites e conta somente leitura;
6. revisão de erros sem expor dados nos logs.

O benchmark público de 512 schemas permanece inalterado para detectar regressões gerais. Critério: relatório comparando adapter da fase 1, adapter especializado e baseline.

### 5. Runtime agentic conectado ao banco

Implementar ferramentas com contratos explícitos: `get_database_profile`, `get_table_schema` e `execute_readonly_sql`. A máquina de estados deve permitir no máximo um ciclo de reparo após erro de execução e bloquear qualquer comando fora da política. Critério: testes automatizados de caminho feliz, rejeição de escrita, schema desconhecido, timeout e reparo limitado.

## Ordem de execução

- [ ] Receber e classificar os materiais privados.
- [ ] Definir dialeto, ambiente de homologação e política de acesso.
- [ ] Implementar snapshot e hash do schema.
- [ ] Construir e auditar as divisões privadas.
- [ ] Treinar o adapter da fase 2.
- [ ] Rodar avaliação privada e regressão pública.
- [ ] Integrar executor somente leitura e observabilidade redigida.
- [ ] Registrar decisões, manifestos e próximos riscos.

## Riscos a acompanhar

- O modelo memorizar termos do domínio, mas falhar quando o schema evoluir; o schema em tempo de uso continua obrigatório.
- Poucos exemplos privados cobrirem apenas consultas simples; priorizar cobertura de joins, agregações, filtros temporais, aliases e casos ambíguos.
- Avaliação que dependa somente de *exact match*; combinar métricas estruturais, segurança e execução controlada.
- Conexão de desenvolvimento ganhar privilégios excessivos; usar conta separada, lista de comandos permitidos, timeout e limite de linhas.

## Critério de encerramento da fase 2

A fase está pronta para uma integração assistida quando existir um adapter versionado localmente, avaliação privada separada, regressão pública registrada, executor com credencial somente leitura e evidências de que consultas proibidas são bloqueadas de forma determinística.
