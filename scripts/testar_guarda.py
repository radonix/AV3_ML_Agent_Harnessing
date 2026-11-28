#!/usr/bin/env python3
"""Testes da guarda do Hermes (scripts/guarda_hermes.py). Uso: python3 scripts/testar_guarda.py"""
import json
import subprocess
import sys
from pathlib import Path

GUARDA = Path(__file__).with_name("guarda_hermes.py")

# (descrição, ferramenta, entrada, deve_permitir)
CASOS = [
    ("estrutura da planilha", "terminal", {"command": "head -n 5 dados/vendas.csv"}, True),
    ("validação (tarefa 1)", "terminal", {"command": "python3 scripts/validar_planilha.py dados/vendas.csv -o saidas/relatorio_qualidade.md"}, True),
    ("resumo da qualidade", "terminal", {"command": "python3 scripts/resumir_qualidade.py saidas/relatorio_qualidade.md"}, True),
    ("limpeza (tarefa 2)", "terminal", {"command": "python3 scripts/limpar_vendas.py dados/vendas.csv -o saidas/vendas_limpas.csv --log saidas/log_limpeza.md"}, True),
    ("verificação (tarefa 2)", "terminal", {"command": "python3 scripts/verificar_limpeza.py dados/vendas.csv saidas/vendas_limpas.csv saidas/log_limpeza.md"}, True),
    ("espaços extras", "terminal", {"command": "  head  -n 5   dados/vendas.csv "}, True),
    ("ler planilha inteira", "terminal", {"command": "cat dados/vendas.csv"}, False),
    ("head com mais linhas", "terminal", {"command": "head -n 500 dados/vendas.csv"}, False),
    ("sobrescrever dados/", "terminal", {"command": "python3 scripts/validar_planilha.py dados/vendas.csv -o dados/vendas.csv"}, False),
    ("redirecionar", "terminal", {"command": "head -n 5 dados/vendas.csv > saidas/x.csv"}, False),
    ("encadear com ;", "terminal", {"command": "head -n 5 dados/vendas.csv; rm -rf dados"}, False),
    ("encadear com &&", "terminal", {"command": "head -n 5 dados/vendas.csv && rm dados/vendas.csv"}, False),
    ("pipe", "terminal", {"command": "head -n 5 dados/vendas.csv | tee dados/x"}, False),
    ("substituição de comando", "terminal", {"command": "head -n 5 dados/$(rm -rf dados)"}, False),
    ("subir de pasta", "terminal", {"command": "head -n 5 dados/../.env"}, False),
    ("ler .env", "terminal", {"command": "head -n 5 .env"}, False),
    ("python arbitrário", "terminal", {"command": "python3 -c 'import os'"}, False),
    ("comando permitido em 2º plano", "terminal", {"command": "head -n 5 dados/vendas.csv", "background": True}, False),
    ("timeout no limite", "terminal", {"command": "head -n 5 dados/vendas.csv", "timeout": 600}, True),
    ("timeout acima do limite", "terminal", {"command": "head -n 5 dados/vendas.csv", "timeout": 10000}, False),
    ("nova linha", "terminal", {"command": "head -n 5 dados/vendas.csv\nrm dados/vendas.csv"}, False),
    ("ferramenta de escrita", "write_file", {"path": "dados/vendas.csv", "content": "x"}, False),
    ("ferramenta sob demanda", "tool_call", {"calls": [{"name": "process_manage", "arguments": {}}]}, False),
]


def main() -> int:
    falhas = 0
    for desc, ferramenta, entrada, permitir in CASOS:
        evento = {"hook_event_name": "pre_tool_call", "tool_name": ferramenta, "tool_input": entrada}
        r = subprocess.run([sys.executable, str(GUARDA)], input=json.dumps(evento), capture_output=True, text=True)
        resposta = json.loads(r.stdout)
        permitiu = resposta.get("action") != "block"
        ok = permitiu == permitir
        falhas += not ok
        print(f"{'OK  ' if ok else 'FALHA'} {desc}: {'permitido' if permitiu else 'bloqueado'}")
    print(f"\n{len(CASOS) - falhas}/{len(CASOS)} testes passaram")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
