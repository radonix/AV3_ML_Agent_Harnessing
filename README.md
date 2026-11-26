# AV3 — Agent Harness Engineering

Agentes em sequência para gerar relatórios de vendas (a saída de um é a entrada do próximo), executados e comparados em duas plataformas, **OpenCode** e **Hermes Agent**, com o modelo `openai/gpt-oss-20b` no GroqCloud. Em todas as tarefas, o modelo só coordena: contagens e correções vêm de scripts em pandas.

## Estrutura
- `AGENTS.md`: regras gerais dos agentes.
- `prompts/<tarefa>_plataformas.md`: instrução de cada tarefa, igual nas duas plataformas.
- `casos/<tarefa>.txt`: casos de teste de cada tarefa (preparo e arquivos esperados).
- `opencode.json`: modelo e permissões do OpenCode (negação por padrão).
- `hermes/config.yaml` e `scripts/guarda_hermes.py`: configuração do Hermes e guarda de comandos (lista de permissão).
- `scripts/`: scripts das tarefas, gerador de dados de teste, coleta de métricas e testes.
- `gabaritos/`: resultado esperado da limpeza (Tarefa 2) em cada caso.
- `dados/`: planilha de entrada, somente leitura durante as execuções. `saidas/`: tudo que os agentes produzem.
- `evidencias/<plataforma>/<tarefa>/<caso>_<data>/` e `evidencias/resumos/`: registros de cada execução.
- `docs/`: documentação por tarefa.

## Casos de teste
A mesma numeração vale para todas as tarefas:

| Caso | Situação |
| --- | --- |
| `caso1` | Duplicatas e datas inválidas |
| `caso2` | Vários problemas nos dados |
| `caso3` | Arquivo vazio |
| `caso4` | Planilha sem erros |

## Rodar
    ./setup.sh                      # venv, OpenCode, Hermes + plugin do Groq, .env
    # edite o .env e coloque a GROQ_API_KEY
    ./run.sh                        # todas as tarefas: primeiro no OpenCode, depois no Hermes
    ./run.sh -p hermes -t tarefa1_validacao -c caso1
    ./run.sh -h                     # todas as opções

Testes sem o modelo: `python3 scripts/testar_limpeza.py` e `python3 scripts/testar_guarda.py`.

Regras: o agente só lê `dados/` e `saidas/`, e só grava em `saidas/`. Nunca versione o `.env`.
