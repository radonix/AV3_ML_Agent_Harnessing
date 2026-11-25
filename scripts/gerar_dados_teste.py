#!/usr/bin/env python3
"""Gera planilhas SINTÉTICAS (sem dados pessoais) para os casos de teste das Tarefas 1 e 2.

Uso:  python3 scripts/gerar_dados_teste.py caso1 [--destino dados] [--xlsx]
                                                [--gabarito gabaritos/caso1]
Casos: caso1 (5 duplicatas + 3 datas inválidas), caso2 (limpa), caso3 (sem coluna
`vendedor`), caso4 (arquivo vazio), caso6 (vários problemas plantados),
caso7 (formatos mistos: datas DD/MM/AAAA, "R$ 3.500,00", grafias de região, produto e
vendedor, valor_total vazio e uma duplicata que só aparece depois de padronizar).
O caso 5 (gravar em dados/) é um teste de segurança da plataforma, não de dados.

--gabarito grava `vendas_limpas.csv` com o resultado ESPERADO da limpeza (Tarefa 2),
montado a partir da planilha base e do que foi plantado, sem usar limpar_vendas.py.
Nos casos 3 e 4 a limpeza deve falhar e não há gabarito.
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
NOMES_UF = {"SP": "São Paulo", "RJ": "Rio de Janeiro", "MG": "Minas Gerais",
            "PR": "Paraná", "RS": "Rio Grande do Sul"}
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
    if caso == "caso7":
        for i in range(30):                              # 30 datas em DD/MM/AAAA
            df.at[i, "data"] = date.fromisoformat(df.at[i, "data"]).strftime("%d/%m/%Y")
        for i in range(30, 40):                          # 10 linhas com valores "brasileiros"
            df.at[i, "preco_unitario"] = "R$ " + br(float(df.at[i, "preco_unitario"]))
            df.at[i, "valor_total"] = br(float(df.at[i, "valor_total"]))
        uf = {i: df.at[i, "regiao"] for i in range(40, 45)}
        df.at[40, "regiao"] = f" {uf[40].lower()} "      # 5 grafias de região
        df.at[41, "regiao"] = NOMES_UF[uf[41]]
        df.at[42, "regiao"] = sem_acento(NOMES_UF[uf[42]]).lower()
        df.at[43, "regiao"] = NOMES_UF[uf[43]].upper()
        df.at[44, "regiao"] = uf[44].lower()
        df.at[45, "produto"] = df.at[45, "produto"].lower()   # 3 grafias de produto
        df.at[46, "produto"] = f"  {df.at[46, 'produto']}  "
        df.at[47, "produto"] = df.at[47, "produto"].upper()
        df.at[48, "vendedor"] = df.at[48, "vendedor"].lower()  # 1 grafia de vendedor
        df.at[49, "valor_total"] = ""                     # 1 valor_total vazio
        copia = df.iloc[[100]].copy()                     # duplicata só após padronizar
        copia["regiao"] = NOMES_UF[copia.iloc[0]["regiao"]]
        copia["produto"] = copia.iloc[0]["produto"].upper()
        df = pd.concat([df, copia], ignore_index=True)
        return df, {"datas_barra": 30, "valores_br": 10, "regiao_grafias": 5,
                    "produto_grafias": 3, "vendedor_grafias": 1, "valor_total_vazio": 1,
                    "duplicata_apos_padronizar": 1}
    raise SystemExit(f"caso desconhecido: {caso}")


def br(x: float) -> str:
    """3500.0 -> '3.500,00' (formato brasileiro)."""
    return f"{x:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def sem_acento(s: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def gabarito(caso: str) -> pd.DataFrame | None:
    """Resultado esperado da Tarefa 2, montado SEM o script de limpeza.

    Parte da planilha base (que já está no formato final) e desfaz o que foi plantado,
    seguindo as regras fixas documentadas em docs/tarefa2_limpeza.md.
    """
    df = base()
    if caso in ("caso2", "caso7"):        # caso7: tudo volta ao formato da base;
        return df                          # a duplicata após padronizar sai
    if caso == "caso1":                    # duplicatas saem; 3 datas inválidas: linha removida
        return df.drop(index=[20, 60, 90]).reset_index(drop=True)
    if caso == "caso6":
        df.loc[[1, 2], "produto"] = "Não informado"      # R8: texto vazio preenchido
        # linhas 3 e 4: quantidade vazia é deduzida (valor_total ÷ preço) -> igual à base
        df.at[5, "quantidade"] = "-3"                    # R7: devolução mantida
        df.at[5, "valor_total"] = str(round(-3 * float(df.at[5, "preco_unitario"]), 2))
        # "São Paulo" -> "SP" (igual à base); linhas 7 e 8: valor_total recalculado (= base)
        df.at[9, "quantidade"] = "9999"                  # R11: atípico mantido
        df.at[9, "valor_total"] = str(round(9999 * float(df.at[9, "preco_unitario"]), 2))
        return df.drop(index=[6]).reset_index(drop=True)  # R7: preço negativo -> removida
    return None                             # caso3 e caso4: a limpeza deve falhar


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
    ap.add_argument("--gabarito", type=Path,
                    help="pasta onde gravar vendas_limpas.csv esperado (Tarefa 2)")
    a = ap.parse_args()
    print(gravar(a.caso, a.destino, a.xlsx))
    if a.gabarito:
        g = gabarito(a.caso)
        if g is None:
            print(f"(sem gabarito para {a.caso}: a limpeza deve falhar)")
        else:
            a.gabarito.mkdir(parents=True, exist_ok=True)
            g.to_csv(a.gabarito / "vendas_limpas.csv", index=False)
            print(a.gabarito / "vendas_limpas.csv")
