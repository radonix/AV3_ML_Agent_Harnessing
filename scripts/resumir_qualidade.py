#!/usr/bin/env python3
"""Imprime um resumo compacto do relatório de qualidade da Tarefa 1.

Serve para o agente "ler" o relatório sem colocar o arquivo inteiro no contexto
(as plataformas só permitem `head -n 5`). Só LÊ; não grava nada.

Uso:
    python3 scripts/resumir_qualidade.py [saidas/relatorio_qualidade.md]

Códigos de saída: 0 resumo impresso; 2 relatório inexistente.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from limpar_vendas import ler_relatorio_t1, tratamento  # noqa: E402

MAX_LINHAS = 15


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    caminho = Path(argv[0]) if argv else Path("saidas/relatorio_qualidade.md")
    info = ler_relatorio_t1(caminho)
    if not info["existe"]:
        print(f"ERRO: relatório da Tarefa 1 não encontrado: {caminho}. Rode a Tarefa 1 antes.")
        return 2
    if info["erro_entrada"]:
        print(f"Relatório da Tarefa 1: ERRO NA ENTRADA (planilha não validada). Arquivo: {info['arquivo']}")
        return 0
    probs = info["problemas"]
    print(f"Relatório da Tarefa 1: arquivo {info['arquivo']} | linhas {info['linhas']} | "
          f"tipos de problema {len(probs)}")
    for col, tipo, q in probs[:MAX_LINHAS]:
        print(f"- {col} | {tipo} | {q} -> {tratamento(col, tipo)}")
    if len(probs) > MAX_LINHAS:
        print(f"... (+{len(probs) - MAX_LINHAS}; veja o relatório)")
    if not probs:
        print("Nenhum problema listado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
