#!/usr/bin/env python3
"""Gera planilhas SINTÉTICAS (sem dados pessoais) para os casos de teste da Tarefa 1.

Uso:  python3 scripts/gerar_dados_teste.py caso1 [--destino dados] [--xlsx]
Casos: caso1 (5 duplicatas + 3 datas inválidas), caso2 (limpa), caso3 (sem coluna
`vendedor`), caso4 (arquivo vazio), caso6 (vários problemas plantados).
O caso 5 (gravar em dados/) é um teste de segurança da plataforma, não de dados.
"""
from __future__ import annotations

import argparse
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

PRODUTOS = [("Notebook", "Eletrônicos", 3500.0), ("Mouse", "Acessórios", 80.0),
            ("Teclado", "Acessórios", 150.0), ("Monitor", "Eletrônicos", 900.0),
            ("Cadeira", "Móveis", 700.0), ("Mesa", "Móveis", 1200.0)]
REGIOES = ["SP", "RJ", "MG", "PR", "RS"]
VENDEDORES = ["Ana", "Bruno", "Carla", "Diego", "Elisa"]
INICIO = date(2026, 1, 1)


def base(n: int = 500, seed: int = 42) -> pd.DataFrame:
    rnd = random.Random(seed)
    linhas = []
    for i in range(1, n + 1):
        prod, cat, preco = rnd.choice(PRODUTOS)
        q = rnd.randint(1, 10)
        linhas.append({
            "data": (INICIO + timedelta(days=rnd.randint(0, 180))).isoformat(),
            "pedido_id": f"PED-{i:05d}", "produto": prod, "categoria": cat,
            "regiao": rnd.choice(REGIOES), "vendedor": rnd.choice(VENDEDORES),
            "quantidade": q, "preco_unitario": preco, "valor_total": round(q * preco, 2)})
    return pd.DataFrame(linhas).astype(str)


def gerar(caso: str) -> tuple[pd.DataFrame | None, dict]:
    """Retorna (DataFrame, esperado). esperado = contagens que o relatório deve trazer."""
    df = base()
    if caso == "caso1":
        for i in (10, 50, 100, 150, 200):               # 5 duplicatas exatas
            df = pd.concat([df, df.iloc[[i]]], ignore_index=True)
        for i, v in ((20, "2026-02-30"), (60, "31/04/2026"), (90, "abc")):
            df.at[i, "data"] = v                         # 3 datas inválidas
        return df, {"duplicatas": 5, "datas_invalidas": 3}
    if caso == "caso2":
        return df, {}
    if caso == "caso3":
        return df.drop(columns=["vendedor"]), {"ausentes": ["vendedor"]}
    if caso == "caso4":
        return None, {"fatal": True}
    if caso == "caso6":
        df.loc[[1, 2], "produto"] = ""                   # 2 nulos em produto
        df.loc[[3, 4], "quantidade"] = ""                # 2 nulos em quantidade
        df.at[5, "quantidade"] = "-3"                    # negativos (valor_total coerente)
        df.at[5, "valor_total"] = str(round(-3 * float(df.at[5, "preco_unitario"]), 2))
        df.at[6, "preco_unitario"] = "-10"
        df.at[6, "valor_total"] = str(round(float(df.at[6, "quantidade"]) * -10, 2))
        idx_sp = list(df.index[df["regiao"] == "SP"][:6])
        df.loc[idx_sp, "regiao"] = "São Paulo"            # 6 linhas com grafia diferente
        df.at[7, "valor_total"] = "1.00"                  # divergência
        df.at[8, "valor_total"] = "2.00"                  # divergência
        df.at[9, "quantidade"] = "9999"                   # atípico (aviso)
        df.at[9, "valor_total"] = str(round(9999 * float(df.at[9, "preco_unitario"]), 2))
        return df, {"nulos_produto": 2, "nulos_quantidade": 2, "negativos": 2,
                    "regiao_grafias": 6, "divergencias": 2}
    raise SystemExit(f"caso desconhecido: {caso}")


def gravar(caso: str, destino: Path, xlsx: bool = False) -> Path:
    destino.mkdir(parents=True, exist_ok=True)
    df, _ = gerar(caso)
    alvo = destino / ("vendas.xlsx" if xlsx else "vendas.csv")
    if df is None:
        alvo.write_bytes(b"")
    elif xlsx:
        df.to_excel(alvo, index=False)
    else:
        df.to_csv(alvo, index=False)
    return alvo


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("caso")
    ap.add_argument("--destino", type=Path, default=Path("dados"))
    ap.add_argument("--xlsx", action="store_true")
    a = ap.parse_args()
    print(gravar(a.caso, a.destino, a.xlsx))
