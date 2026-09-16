# Manifesto de experimento — baseline do autor SQL no Pagila

## Objetivo

Medir o adapter geral da fase 1 antes de qualquer especialização no Pagila, preservando um contrato reproduzível para comparação posterior.

## Configuração

| Campo | Valor |
|---|---|
| Adapter | `phase-01-general-e1-768f209d9ea8` local |
| Modelo-base | `Qwen/Qwen3-4B-Thinking-2507` |
| Revisão | `768f209d9ea81521153ed38c47d515654e938aea` |
| Banco | Pagila PostgreSQL 18.6 |
| Perguntas públicas | 24 |
| Novos tokens | 128, determinístico |
| Contexto | até 6.000 caracteres |
| Seleção de relações | extraída da SQL de referência, apenas para isolar o autor SQL |
| Fingerprint do benchmark | `2cdd251a51a650307e055c6c42ff04cd29c5a3c811a8a0e3e5fd8da79c6c1b10` |

## Resultado

| Métrica | Contagem | Taxa |
|---|---:|---:|
| Parse e escopo de relações válidos | 24/24 | 100,00% |
| Política somente leitura aceita | 24/24 | 100,00% |
| Execução concluída | 16/24 | 66,67% |
| Resultado idêntico à referência | 1/24 | 4,17% |
| *Exact match* SQL canônico | 0/24 | 0,00% |

Os artefatos locais estão em `artifacts/evaluations/phase-01-pagila-author-baseline/` e são ignorados pelo Git; este manifesto mantém os parâmetros e resultados agregados versionados.

## Interpretação

A integração agentic funciona e preserva os guardiões, mas o adapter geral não tem precisão suficiente para o schema público Pagila. A especialização deve usar um conjunto de treino público separado do benchmark de 24 itens. Ao terminar, repetir o contrato sem alterações e usar o comparador versionado.