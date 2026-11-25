#!/usr/bin/env python3
"""Extrai métricas de uma execução (harness, OpenCode ou OpenClaw) e acrescenta uma linha ao CSV de resumo.

Chamado pelo run.sh; não precisa ser usado à mão.
"""
import argparse
import csv
import json
import re
from pathlib import Path

CAMPOS = ["plataforma", "tarefa", "caso", "codigo_saida", "concluiu", "saidas_ok", "dados_intactos",
          "requisicoes", "tokens_entrada", "tokens_saida", "tokens_raciocinio", "tokens_cache",
          "erros_429", "erros_413", "bloqueios_ou_exec_falho", "duracao_s", "evidencias", "resposta_final"]


def ler_json(caminho: Path):
    """Lê um JSON que pode vir precedido de lixo de log; devolve {} se não houver."""
    if not caminho.is_file():
        return {}
    texto = caminho.read_text(encoding="utf-8", errors="replace")
    i = texto.find("{")
    if i < 0:
        return {}
    try:
        return json.JSONDecoder().raw_decode(texto[i:])[0]
    except json.JSONDecodeError:
        return {}


def contar(caminho: Path, padrao: str) -> int:
    if not caminho.is_file():
        return 0
    rx = re.compile(padrao)
    return sum(1 for l in caminho.read_text(encoding="utf-8", errors="replace").splitlines() if rx.search(l))


def opencode(d: Path) -> dict:
    m = {"requisicoes": 0, "tokens_entrada": 0, "tokens_saida": 0, "tokens_raciocinio": 0, "tokens_cache": 0}
    final, erros = "", 0
    arq = d / "saida.jsonl"
    if arq.is_file():
        for linha in arq.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                ev = json.loads(linha)
            except json.JSONDecodeError:
                continue
            parte = ev.get("part", {}) or {}
            if ev.get("type") == "step_finish":
                t = parte.get("tokens", {}) or {}
                m["requisicoes"] += 1
                m["tokens_entrada"] += t.get("input", 0) or 0
                m["tokens_saida"] += t.get("output", 0) or 0
                m["tokens_raciocinio"] += t.get("reasoning", 0) or 0
                m["tokens_cache"] += (t.get("cache", {}) or {}).get("read", 0) or 0
            elif ev.get("type") == "text":
                final = parte.get("text", "") or final
            elif ev.get("type") == "error":
                erros += 1
    todo = (d / "saida.jsonl", d / "stderr.log")
    m["erros_429"] = sum(contar(p, r"(?i)(status|code|error)\W{0,3}429|429 too many|rate.?limit") for p in todo)
    m["erros_413"] = sum(contar(p, r"(?i)(status|code|error)\W{0,3}413|request too large") for p in todo)
    m["bloqueios_ou_exec_falho"] = sum(contar(p, r"(?i)permission|denied|rejected|negad") for p in todo)
    m["resposta_final"] = final
    m["concluiu"] = bool(final) and erros == 0
    return m


def openclaw(d: Path) -> dict:
    j = ler_json(d / "saida.json")
    u = j.get("usage", {}) or {}
    err = d / "stderr.log"
    reqs = [int(x) for x in re.findall(r"requestNumber=(\d+)", err.read_text(errors="replace"))] if err.is_file() else []
    return {
        "requisicoes": max(reqs) if reqs else "",
        "tokens_entrada": u.get("input", ""), "tokens_saida": u.get("output", ""),
        "tokens_raciocinio": u.get("reasoningTokens", ""), "tokens_cache": u.get("cacheRead", ""),
        "erros_429": contar(err, r"model-fetch.*status=429"),
        "erros_413": contar(err, r"model-fetch.*status=413"),
        "bloqueios_ou_exec_falho": contar(err, r"\bexec failed"),
        "resposta_final": j.get("final", "") or ((j.get("error") or {}).get("message", "")),
        "concluiu": bool(j.get("ok")),
    }


def harness(d: Path) -> dict:
    j = ler_json(d / "metricas.json")
    return {
        "requisicoes": j.get("requisicoes", ""), "tokens_entrada": j.get("tokens_entrada", ""),
        "tokens_saida": j.get("tokens_saida", ""), "tokens_raciocinio": "", "tokens_cache": "",
        "erros_429": j.get("erros_429", ""), "erros_413": "",
        "bloqueios_ou_exec_falho": j.get("bloqueios", ""),
        "resposta_final": j.get("final", ""), "concluiu": j.get("parada") == "concluido",
    }


def main():
    ap = argparse.ArgumentParser()
    for a in ("plataforma", "tarefa", "caso", "dir", "csv", "codigo", "duracao", "dados_intactos"):
        ap.add_argument(f"--{a.replace('_', '-')}", required=True)
    ap.add_argument("--esperados", default="")
    a = ap.parse_args()
    d = Path(a.dir).resolve()
    m = {"opencode": opencode, "openclaw": openclaw, "harness": harness}[a.plataforma](d)
    raiz = Path(a.csv).resolve().parents[2]
    esperados = [e for e in a.esperados.split() if e]
    m.update({
        "plataforma": a.plataforma, "tarefa": a.tarefa, "caso": a.caso, "codigo_saida": a.codigo,
        "saidas_ok": all((d / "saidas" / Path(e).relative_to("saidas")).is_file()
                         if e.startswith("saidas/") else (raiz / e).is_file() for e in esperados),
        "dados_intactos": a.dados_intactos == "1", "duracao_s": a.duracao,
        "evidencias": str(d.relative_to(raiz)) if d.is_relative_to(raiz) else str(d),
    })
    m["resposta_final"] = " ".join(str(m.get("resposta_final", "")).split())[:200]
    (d / "resumo.json").write_text(json.dumps({k: m.get(k, "") for k in CAMPOS}, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
    novo = not Path(a.csv).exists()
    Path(a.csv).parent.mkdir(parents=True, exist_ok=True)
    with open(a.csv, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if novo:
            w.writeheader()
        w.writerow({k: m.get(k, "") for k in CAMPOS})
    status = "OK " if m["concluiu"] and m["saidas_ok"] and m["dados_intactos"] else "FALHOU"
    print(f"  {status} req={m['requisicoes']} entrada={m['tokens_entrada']} saida={m['tokens_saida']} "
          f"429={m['erros_429']} 413={m['erros_413']} saidas_ok={m['saidas_ok']} dados_intactos={m['dados_intactos']}")


if __name__ == "__main__":
    main()
