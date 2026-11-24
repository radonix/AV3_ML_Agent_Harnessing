# AV3 — Agent Harness Engineering

Cinco agentes em sequência para gerar relatórios de vendas (a saída de um é a entrada do próximo), todos com o mesmo harness (`agentes/base.py`) e o modelo `openai/gpt-oss-20b` no GroqCloud.

## Estrutura
- `agentes/base.py`: laço do agente, ferramentas (`write_file`, `run_command`), controle de 429 e métricas.
- `agentes/tarefaN_*.py`: só a configuração de cada tarefa (prompt e pastas permitidas). Tarefas 2 a 5 são rascunhos.
- `scripts/`: código de referência da equipe e gerador de dados de teste.
- `dados/`: planilha original, somente leitura. `saidas/`: tudo que os agentes produzem.
- `docs/`: documentação por tarefa. `evidencias/<tarefa>/<execucao>/`: métricas e conversa de cada rodada.

## Rodar
    pip install -r requirements.txt
    cp .env.example .env            # coloque sua chave do GroqCloud
    python3 scripts/gerar_dados_teste.py caso1
    python -m agentes.tarefa1_validacao --exec exec01

Regras: o agente só lê `dados/` e `saidas/`, e só grava em `saidas/`. Nunca versione o `.env`.
