#!/usr/bin/env python3
"""Verificação automática da Tarefa 2: confere o CSV limpo e o log contra a entrada.

Só LÊ arquivos; não grava nada. Não usa o código de limpeza para decidir o que é
certo: recalcula tudo a partir da planilha bruta, do CSV limpo e do log.

Checagens:
  1. CSV limpo existe e tem as colunas na ordem esperada
  2. Log traz o bloco de contagens
  3. Contagens do log batem com os arquivos (antes, depois, removidas, alteradas)
  4. Toda linha removida ou alterada tem justificativa nas tabelas do log
  5. As linhas mantidas são as da entrada, na mesma ordem (pedido_id)
  6. Nenhuma alteração silenciosa: todo valor que mudou está numa linha registrada
  7. Nenhuma duplicata exata
  8. Nenhum formato fora do padrão (datas, números, região, vazios, espaços)
  9. valor_total = quantidade × preco_unitario (±0,01)
 10. (opcional, --gabarito) mesmas linhas e valores do gabarito limpo

Uso:
    python3 scripts/verificar_limpeza.py [dados/vendas.csv] [saidas/vendas_limpas.csv]
        [saidas/log_limpeza.md] [--gabarito gabaritos/caso1/vendas_limpas.csv]

Códigos de saída: 0 todas as checagens OK; 1 alguma falhou.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validar_planilha import COLUNAS, NUMERICAS, UFS, eh_nulo, ler, parse_num  # noqa: E402

NAO_INFORMADO = "Não informado"
RE_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_INT = re.compile(r"^-?\d+$")
RE_DEC2 = re.compile(r"^-?\d+\.\d{2}$")
SIGLAS = {s.upper() for s in UFS}


class Verificacao:
    def __init__(self):
        self.itens = []

    def item(self, ok: bool, texto: str, detalhe: str = ""):
        self.itens.append(ok)
        print(("OK    " if ok else "FALHA ") + texto + (f" ({detalhe})" if detalhe and not ok else ""))
        return ok


def ler_csv(p: Path) -> pd.DataFrame:
    return pd.read_csv(p, dtype=str, keep_default_na=False, encoding="utf-8")


def linhas_justificadas(texto_log: str) -> dict:
    """Números de linha com justificativa nas seções 6 (removidas) e 7 (alteradas)."""
    secoes = {"6": set(), "7": set()}
    atual = None
    for lin in texto_log.splitlines():
        m = re.match(r"^## (\d+)\.", lin)
        if m:
            atual = m[1] if m[1] in secoes else None
            continue
        if atual:
            m = re.match(r"^\| (\d+) \| .+ \| (.+) \|$", lin)
            if m and m[2].strip():
                secoes[atual].add(int(m[1]))
    return secoes


def mudou(col: str, bruto: str, limpo: str) -> bool:
    if col in NUMERICAS:
        x = parse_num(bruto) if not eh_nulo(bruto) else None
        try:
            return x is None or abs(x - float(limpo)) > 1e-9
        except ValueError:
            return True
    return bruto != limpo


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("entrada", nargs="?", type=Path, default=Path("dados/vendas.csv"))
    ap.add_argument("limpa", nargs="?", type=Path, default=Path("saidas/vendas_limpas.csv"))
    ap.add_argument("log", nargs="?", type=Path, default=Path("saidas/log_limpeza.md"))
    ap.add_argument("--gabarito", type=Path)
    a = ap.parse_args(argv)
    v = Verificacao()

    # 1 e 2: arquivos
    if not v.item(a.limpa.exists(), "1 CSV limpo existe", str(a.limpa)):
        print("Verificação interrompida: sem CSV limpo.")
        return 1
    limpa = ler_csv(a.limpa)
    extras = [c for c in limpa.columns if c not in COLUNAS]
    v.item(list(limpa.columns[:len(COLUNAS)]) == COLUNAS, "1 colunas na ordem esperada",
           f"encontrado: {list(limpa.columns)}")
    texto_log = a.log.read_text(encoding="utf-8") if a.log.exists() else ""
    m = re.search(r"```json\n(.+?)\n```", texto_log, re.S)
    if not v.item(bool(m), "2 log com bloco de contagens", str(a.log)):
        print("Verificação interrompida: log sem contagens.")
        return 1
    n = json.loads(m[1])
    try:
        bruta = ler(a.entrada)
    except Exception as e:
        v.item(False, "3 entrada legível", f"{type(e).__name__}: {e}")
        return 1
    bruta.columns = [c.strip().lower() for c in bruta.columns]

    # 3: contagens
    v.item(n["linhas_antes"] == len(bruta), f"3 linhas antes = {len(bruta)}",
           f"log diz {n['linhas_antes']}")
    v.item(n["linhas_depois"] == len(limpa), f"3 linhas depois = {len(limpa)}",
           f"log diz {n['linhas_depois']}")
    soma_ok = (n["linhas_antes"] - n["removidas"] == n["linhas_depois"]
               and len(n["linhas_removidas"]) == n["removidas"]
               == sum(n["remocoes_por_motivo"].values())
               and len(n["linhas_alteradas"]) == n["alteradas"])
    v.item(soma_ok, f"3 antes − removidas = depois ({n['linhas_antes']} − {n['removidas']} = "
           f"{n['linhas_depois']}); listas do log coerentes")

    # 4: justificativas
    just = linhas_justificadas(texto_log)
    sem_rem = sorted(set(n["linhas_removidas"]) - just["6"])
    sem_alt = sorted(set(n["linhas_alteradas"]) - just["7"])
    v.item(not sem_rem and not sem_alt, "4 toda linha removida ou alterada está justificada no log",
           f"sem justificativa: removidas {sem_rem[:5]}, alteradas {sem_alt[:5]}")

    # 5: alinhamento entrada x saída
    removidas = set(n["linhas_removidas"])
    mantidas = [i for i in bruta.index if i + 2 not in removidas]
    alinhado = len(mantidas) == len(limpa)
    if alinhado:
        for k, i in enumerate(mantidas):
            bruto_id = re.sub(r"\s+", " ", bruta.at[i, "pedido_id"].strip())
            esperado = NAO_INFORMADO if eh_nulo(bruto_id) else bruto_id
            if limpa.at[k, "pedido_id"] != esperado:
                alinhado = False
                break
    v.item(alinhado, "5 linhas mantidas são as da entrada, na mesma ordem",
           f"{len(mantidas)} esperadas pela lista de removidas, {len(limpa)} no CSV")

    # 6: alteração silenciosa
    silenciosas = []
    if alinhado:
        registradas = set(n["linhas_alteradas"])
        for k, i in enumerate(mantidas):
            if i + 2 in registradas:
                continue
            for c in COLUNAS + extras:
                if c in bruta.columns and mudou(c, bruta.at[i, c], limpa.at[k, c]):
                    silenciosas.append(f"linha {i + 2} {c}: {bruta.at[i, c]!r} → {limpa.at[k, c]!r}")
    v.item(alinhado and not silenciosas, "6 nenhuma alteração silenciosa",
           "; ".join(silenciosas[:3]) or "sem alinhamento")

    # 7: duplicatas
    dup = int(limpa.duplicated().sum())
    v.item(dup == 0, "7 nenhuma duplicata exata", f"{dup} duplicata(s)")

    # 8: formatos
    erros = []

    def data_ok(s):
        if not RE_DATA.match(s):
            return False
        try:
            date.fromisoformat(s)
            return True
        except ValueError:
            return False

    regras = [("data", data_ok), ("quantidade", lambda s: bool(RE_INT.match(s))),
              ("preco_unitario", lambda s: bool(RE_DEC2.match(s))),
              ("valor_total", lambda s: bool(RE_DEC2.match(s))),
              ("regiao", lambda s: s in SIGLAS or s == NAO_INFORMADO)]
    for col, ok in regras:
        ruins = [f"linha {k + 2}: {x!r}" for k, x in limpa[col].items() if not ok(x)]
        if ruins:
            erros.append(f"{col}: {len(ruins)} ({ruins[0]})")
    for col in limpa.columns:
        ruins = [k for k, x in limpa[col].items()
                 if eh_nulo(x) or x != x.strip() or "  " in x]
        if ruins:
            erros.append(f"{col}: {len(ruins)} vazio(s) ou com espaços")
    v.item(not erros, "8 nenhum formato fora do padrão", "; ".join(erros[:3]))

    # 9: valor_total
    try:
        q, p, t = (limpa[c].astype(float) for c in NUMERICAS)
        div = int(((q * p - t).abs() > 0.011).sum())
    except ValueError:
        div = -1
    v.item(div == 0, "9 valor_total = quantidade × preco_unitario",
           f"{div} divergência(s)" if div > 0 else "valores não numéricos")

    # 10: gabarito
    if a.gabarito:
        g = ler_csv(a.gabarito)
        dif = []
        if len(g) == len(limpa):
            for k in range(len(g)):
                for c in COLUNAS:
                    x, y = g.at[k, c], limpa.at[k, c]
                    igual = (abs(float(x) - float(y)) <= 0.01) if c in NUMERICAS else x == y
                    if not igual:
                        dif.append(f"linha {k + 2} {c}: esperado {x!r}, obtido {y!r}")
        v.item(len(g) == len(limpa) and not dif,
               f"10 igual ao gabarito ({len(g)} linhas)",
               f"{len(limpa)} linhas obtidas" if len(g) != len(limpa) else "; ".join(dif[:3]))

    total, oks = len(v.itens), sum(v.itens)
    print(f"Verificação: {oks}/{total} OK" + ("" if oks == total else " — REPROVADA"))
    return 0 if oks == total else 1


if __name__ == "__main__":
    sys.exit(main())
