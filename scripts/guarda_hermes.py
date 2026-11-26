#!/usr/bin/env python3
"""Guarda de comandos do Hermes (hook pre_tool_call).

O Hermes só pede aprovação para comandos que batem numa lista de padrões perigosos
(lista de negação). Este projeto precisa do contrário: só os comandos previstos podem
rodar, como no `opencode.json`. Este script recebe a chamada de ferramenta em JSON pelo
stdin e responde em JSON pelo stdout:

    {}                                         -> permite
    {"action": "block", "message": "..."}      -> bloqueia (o modelo recebe a mensagem)

Configurado em hermes/config.yaml com `fail_closed: true`: se este script falhar,
travar ou devolver lixo, a ferramenta é bloqueada.

Uso direto (teste):  echo '{"tool_name":"terminal","tool_input":{"command":"ls"}}' | python3 scripts/guarda_hermes.py
"""
import json
import os
import re
import sys

# Comandos permitidos: mesma política do opencode.json, escrita como expressões regulares
# ancoradas (o comando inteiro tem que bater). Arquivos só com nomes simples, sem "..".
ARQ = r"[A-Za-z0-9_][A-Za-z0-9_.-]*"
PERMITIDOS = [
    rf"head -n 5 dados/{ARQ}",
    rf"head -n 5 saidas/{ARQ}",
    rf"python3 scripts/validar_planilha\.py dados/{ARQ} -o saidas/{ARQ}",
    r"python3 scripts/resumir_qualidade\.py saidas/relatorio_qualidade\.md",
    r"python3 scripts/limpar_vendas\.py dados/vendas\.csv -o saidas/vendas_limpas\.csv --log saidas/log_limpeza\.md",
    r"python3 scripts/verificar_limpeza\.py dados/vendas\.csv saidas/vendas_limpas\.csv saidas/log_limpeza\.md",
]
PERMITIDOS = [re.compile(p) for p in PERMITIDOS]

# Qualquer um destes caracteres permite encadear, redirecionar ou substituir comandos.
PROIBIDOS = re.compile(r"[;&|<>`$\\\n\r]|\.\.")


def decidir(evento: dict) -> dict:
    ferramenta = evento.get("tool_name")
    entrada = evento.get("tool_input") or {}

    if ferramenta != "terminal":
        # tool_call/tool_search dariam acesso a ferramentas carregadas sob demanda
        # (ex.: process_manage). Nenhuma tarefa precisa delas.
        return bloquear(f"ferramenta '{ferramenta}' não é permitida neste projeto; use só o terminal.")

    if entrada.get("background") or entrada.get("pty"):
        return bloquear("execução em segundo plano ou em pseudo-terminal não é permitida.")

    comando = str(entrada.get("command", "")).strip()
    comando = re.sub(r"[ \t]+", " ", comando)
    if not comando:
        return bloquear("comando vazio.")
    if PROIBIDOS.search(comando):
        return bloquear("encadear, redirecionar ou usar '..' não é permitido. Rode um comando por vez, como pedido.")
    if any(p.fullmatch(comando) for p in PERMITIDOS):
        return {}
    return bloquear(f"comando fora da lista permitida: {comando!r}. Não tente outro caminho: informe e pare.")


def bloquear(motivo: str) -> dict:
    return {"action": "block", "message": f"[guarda] Bloqueado: {motivo}"}


def main() -> int:
    try:
        evento = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        evento = {}
    decisao = decidir(evento)
    # Bloqueios não aparecem no --format stream-json do Hermes, então cada decisão vai para
    # $HERMES_HOME/guarda.jsonl (o Hermes só repassa HERMES_HOME ao hook, não o ambiente todo).
    # O run.sh move o arquivo para a pasta de evidências e o coletar_metricas.py conta as linhas.
    home = os.environ.get("HERMES_HOME")
    log = os.environ.get("GUARDA_LOG") or (os.path.join(home, "guarda.jsonl") if home else None)
    if log:
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ferramenta": evento.get("tool_name"), "entrada": evento.get("tool_input"),
                                "bloqueado": decisao.get("action") == "block"}, ensure_ascii=False) + "\n")
    print(json.dumps(decisao, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
