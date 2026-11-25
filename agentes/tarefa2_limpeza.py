"""Tarefa 2: limpeza e padronização -> saidas/vendas_limpas.csv + saidas/log_limpeza.md

Pré-requisito: saidas/relatorio_qualidade.md da Tarefa 1 (da mesma planilha).
Rodar:  python -m agentes.tarefa2_limpeza --exec caso1
"""
from .base import Config, main

CONFIG = Config(
    nome="tarefa2_limpeza",
    system_prompt=(
        "Você é um agente que limpa planilhas de vendas. Use somente as ferramentas. "
        "Grave arquivos só em saidas/ e nunca altere dados/. "
        "Toda contagem e toda correção vêm de um script, nunca de você. "
        "Arquivos gerados por scripts não devem ser reescritos à mão. "
        "Se uma ferramenta falhar ou não devolver dados, diga isso e não mostre dados que não vieram de uma ferramenta."
    ),
    tarefa=(
        "Tarefa 2: limpe e padronize a planilha de vendas. "
        "Regras fixas, já implementadas no script (não as mude): duplicatas exatas saem; "
        "datas vão para AAAA-MM-DD e linha com data inválida ou vazia sai; "
        "números usam ponto decimal; se falta só um entre quantidade, preço e valor_total, ele é "
        "recalculado pela conta, se faltam dois a linha sai; valor_total divergente é recalculado; "
        "quantidade negativa é devolução e fica; preço negativo ou zero é erro e a linha sai; "
        "texto vazio vira 'Não informado'; região vira sigla de UF ('São Paulo' -> 'SP'); "
        "valores atípicos ficam e vão para revisão humana. "
        "1) Rode 'python3 scripts/resumir_qualidade.py saidas/relatorio_qualidade.md' para ver os problemas apontados na Tarefa 1. "
        "2) Rode 'python3 scripts/limpar_vendas.py dados/vendas.csv -o saidas/vendas_limpas.csv --log saidas/log_limpeza.md'. "
        "Se ele terminar com ERRO, informe o erro e pare. "
        "3) Rode 'python3 scripts/verificar_limpeza.py dados/vendas.csv saidas/vendas_limpas.csv saidas/log_limpeza.md'. "
        "4) Rode 'head -n 5 saidas/vendas_limpas.csv'. "
        "5) Responda com as linhas antes e depois, as remoções e alterações por motivo e o resultado da verificação, "
        "copiados das saídas dos scripts."
    ),
    leitura=("saidas",),   # head só em saidas/; a planilha bruta é lida pelo script, não pelo modelo
    escrita=False,         # quem grava o CSV e o log é o script; sem write_file
    max_loops=8,
)

if __name__ == "__main__":
    main(CONFIG)
