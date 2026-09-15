# Runbook — Ambiente de desenvolvimento

## Pré-requisito

Instalar Python **3.11** e garantir que `python --version` funcione no terminal. O projeto aceita Python 3.11–3.13, mas fixa 3.11 para compatibilidade previsível com treinamento em GPU. A base usa `enum.StrEnum`, disponível a partir do Python 3.11.

Em 2026-09-14 não havia Python executável na máquina: o comando `python` resolveu para o atalho da Microsoft Store. Nenhuma instalação foi feita automaticamente.

## Verificação após instalar Python

No diretório do projeto, execute:

```powershell
python -m unittest discover -s tests -t . -v
```

O resultado esperado inicial é a aprovação da política read-only e da máquina de estados agentic. Só depois criar ambiente virtual e instalar bibliotecas de datasets, treinamento ou inferência.

## Regra de segurança

Não adicionar credenciais de banco a arquivos versionados. A futura configuração local deverá usar `.env`, já ignorado pelo Git, e uma conta de banco com permissões reais somente de leitura.
