# Manifesto de experimento — fase 1 geral, uma época

## Treino

| Campo | Valor |
|---|---:|
| Modelo-base | `Qwen/Qwen3-4B-Thinking-2507` |
| Revisão | `768f209d9ea81521153ed38c47d515654e938aea` |
| Dados de treino | 70.550 exemplos públicos em português |
| Validação periódica | 512 exemplos, isolados por schema |
| Passos | 4.410 |
| Duração | 36.902,960 s (10h15m03s) |
| Perda de treino | 0,07431 |
| Perda de validação final | 0,04679 |

O adapter local está em `artifacts/runs/phase-01-general-e1-768f209d9ea8/` e não entra no Git.

## Benchmark de geração isolado

O benchmark usa uma amostra estratificada, determinística e não vista de 512 schemas da validação pública. Para cada exemplo, a resposta é limitada a 128 novos tokens. Marcadores de protocolo Qwen (`</think>`) são removidos antes de validar SQL; prosa continua inválida.

| Métrica | Modelo-base | Adapter fase 1 |
|---|---:|---:|
| SQL com parse | 0,00% | 100,00% |
| Saída somente SQL normalizada | 0,00% | 100,00% |
| Política read-only | 0,00% | 100,00% |
| Referências válidas ao schema | 0,00% | 98,05% (502/512) |
| *Exact match* canônico | 0,00% | 64,06% (328/512) |

O modelo-base consome sua resposta em raciocínio aberto sob este contrato de 128 tokens e, por isso, não produz SQL utilizável. Esta é uma comparação de aderência ao produto, não uma medida geral de capacidade de raciocínio.

## Resultados por complexidade do adapter

| Complexidade | Exemplos | Referências válidas | *Exact match* |
|---|---:|---:|---:|
| Simples | 287 | 287 (100,00%) | 218 (75,96%) |
| Intermediária | 55 | 55 (100,00%) | 46 (83,64%) |
| Complexa | 170 | 160 (94,12%) | 64 (37,65%) |

Os dez desvios estruturais são erros reais de coluna ou semântica em consultas complexas; por exemplo, `Status_Description` foi gerada onde o schema define `document_status_description`. Isso confirma que o runtime deve manter a validação de schema e a política read-only como barreiras determinísticas.

## Decisão

**Fase 1 aprovada para a especialização privada.** O adapter atende ao contrato de resposta SQL e supera amplamente o modelo-base na tarefa direta. Isso não autoriza execução automática em banco: a fase 2 deve usar schema privado, SQLs validados, credencial read-only e avaliação isolada. O benchmark público acima será repetido após a fase 2 para detectar regressões.
