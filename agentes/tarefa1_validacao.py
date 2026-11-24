"""Tarefa 1: ingestão e validação da planilha -> saidas/relatorio_qualidade.md

Rodar:  python -m agentes.tarefa1_validacao --exec exec01
"""
from .base import Config, main

CONFIG = Config(
    nome="tarefa1_validacao",
    system_prompt=(
        "Você é um agente que valida planilhas de vendas. Use somente as ferramentas. "
        "Grave arquivos só em saidas/ e nunca altere dados/. "
        "Toda contagem vem de um script, nunca de você. "
        "O relatório é gerado pelo script: não o reescreva. "
        "Se uma ferramenta falhar ou não devolver dados, diga isso e não mostre dados que não vieram de uma ferramenta."
    ),
    tarefa=(
        "Tarefa 1: valide a planilha de vendas. "
        "1) Rode 'head -n 5 dados/vendas.csv' para ver a estrutura. "
        "2) Rode 'python3 scripts/validar_planilha.py dados/vendas.csv -o saidas/relatorio_qualidade.md'. "
        "3) Responda com a saída do script."
    ),
    leitura=("dados",),
    escrita=False,   # esta tarefa só executa o script; não precisa de write_file
)

if __name__ == "__main__":
    main(CONFIG)
