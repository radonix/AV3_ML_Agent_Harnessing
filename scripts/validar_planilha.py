#!/usr/bin/env python3
"""Tarefa 1 - Validação de qualidade da planilha de vendas.

Só LÊ a planilha de entrada e só ESCREVE o relatório Markdown de saída.
Todas as contagens vêm deste código (pandas), nunca de estimativa do modelo.

Uso:
    python3 scripts/validar_planilha.py [entrada] [-o saidas/relatorio_qualidade.md]

Sem `entrada`, usa dados/vendas.csv e, se não existir, dados/vendas.xlsx.

Códigos de saída:
    0  relatório gerado (com ou sem problemas nos dados)
    2  entrada inexistente, vazia ou ilegível (relatório de erro é gravado)
    4  caminho de saída recusado (dentro da pasta da entrada, ex.: dados/)
"""
from __future__ import annotations

import argparse
import math
import re
import sys
import unicodedata
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import pandas as pd

COLUNAS = ["data", "pedido_id", "produto", "categoria", "regiao",
           "vendedor", "quantidade", "preco_unitario", "valor_total"]
TEXTO = ["produto", "categoria", "regiao", "vendedor"]
NUMERICAS = ["quantidade", "preco_unitario", "valor_total"]
TOKENS_NULOS = {"", "na", "n/a", "nan", "null", "none", "-", "--"}
K_IQR = 3.0          # limite para valores atípicos (aviso, não é problema)
TOLERANCIA = 0.02    # diferença aceita entre quantidade*preço e valor_total
MAX_EXEMPLOS = 3

UFS = {
    "ac": "acre", "al": "alagoas", "ap": "amapa", "am": "amazonas", "ba": "bahia",
    "ce": "ceara", "df": "distrito federal", "es": "espirito santo", "go": "goias",
    "ma": "maranhao", "mt": "mato grosso", "ms": "mato grosso do sul",
    "mg": "minas gerais", "pa": "para", "pb": "paraiba", "pr": "parana",
    "pe": "pernambuco", "pi": "piaui", "rj": "rio de janeiro",
    "rn": "rio grande do norte", "rs": "rio grande do sul", "ro": "rondonia",
    "rr": "roraima", "sc": "santa catarina", "sp": "sao paulo", "se": "sergipe",
    "to": "tocantins",
}

RE_ISO = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T]00:00:00)?$")
RE_BARRA = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
RE_NUM_PADRAO = re.compile(r"^-?\d+(\.\d+)?$")


# ----------------------------------------------------------------- utilitários
def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def chave(s: str, regiao: bool = False) -> str:
    k = re.sub(r"\s+", " ", sem_acento(s).strip().lower())
    if regiao:
        k = UFS.get(k, k)          # "SP" e "São Paulo" -> "sao paulo"
    return k


def eh_nulo(s: str) -> bool:
    return s.strip().lower() in TOKENS_NULOS


def parse_num(s: str) -> float | None:
    t = s.strip().replace("R$", "").replace(" ", "")
    if not t:
        return None
    if "," in t and "." in t:
        if t.rfind(",") > t.rfind("."):
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        v = float(t)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def parse_data_iso(s: str) -> date | None:
    m = RE_ISO.match(s.strip())
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError:
        return None


def esc(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def ex_linha(i: int, valor: str) -> str:
    return f"linha {i + 2}: {valor!r}"          # linha 1 = cabeçalho


# ---------------------------------------------------------------------- leitura
def ler(caminho: Path) -> pd.DataFrame:
    if not caminho.exists():
        raise FileNotFoundError(f"arquivo inexistente: {caminho}")
    if caminho.stat().st_size == 0:
        raise ValueError("arquivo vazio (0 bytes)")
    ext = caminho.suffix.lower()
    if ext == ".xlsx":
        df = pd.read_excel(caminho, dtype=str, engine="openpyxl").fillna("")
    elif ext in (".csv", ".txt"):
        try:
            df = pd.read_csv(caminho, dtype=str, keep_default_na=False,
                             sep=None, engine="python", encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(caminho, dtype=str, keep_default_na=False,
                             sep=None, engine="python", encoding="latin-1")
    else:
        raise ValueError(f"formato não suportado: {ext} (use .csv ou .xlsx)")
    df.columns = [str(c) for c in df.columns]
    if len(df) == 0:
        raise ValueError("planilha sem linhas de dados (apenas cabeçalho)")
    return df


# ------------------------------------------------------------------- verificações
def problema(col, tipo, qtd, exemplos):
    return {"coluna": col, "tipo": tipo, "quantidade": int(qtd),
            "exemplos": list(exemplos)[:MAX_EXEMPLOS]}


def checar_datas(serie: pd.Series, problemas: list, avisos: list) -> None:
    iso, barra, invalidas = [], [], []
    for i, v in serie.items():
        if eh_nulo(v):
            continue
        s = v.strip()
        if RE_ISO.match(s):
            iso.append(i)
            if parse_data_iso(s) is None:
                invalidas.append(i)
        elif RE_BARRA.match(s):
            barra.append(i)
        else:
            invalidas.append(i)

    # convenção das datas com barra, deduzida pelas evidências da própria coluna
    pares = {i: tuple(int(x) for x in RE_BARRA.match(serie[i].strip()).groups()[:2])
             for i in barra}
    ev_dm = any(a > 12 for a, _ in pares.values())      # 25/03 só pode ser dd/mm
    ev_md = any(b > 12 for _, b in pares.values())      # 03/25 só pode ser mm/dd
    mistura_dm_md = ev_dm and ev_md

    def valida(i, ordem):
        a, b = pares[i]
        d, m = (a, b) if ordem == "dm" else (b, a)
        y = int(RE_BARRA.match(serie[i].strip())[3])
        try:
            date(y, m, d)
            return True
        except ValueError:
            return False

    ordem = "md" if (ev_md and not ev_dm) else "dm"
    for i in barra:
        ok = (valida(i, "dm") or valida(i, "md")) if mistura_dm_md else valida(i, ordem)
        if not ok:
            invalidas.append(i)

    if invalidas:
        invalidas = sorted(set(invalidas))
        problemas.append(problema("data", "data inválida", len(invalidas),
                                  (ex_linha(i, serie[i]) for i in invalidas)))
    inv = set(invalidas)
    iso_ok = [i for i in iso if i not in inv]       # formato só conta se a data é válida
    barra_ok = [i for i in barra if i not in inv]
    if iso_ok and barra_ok:
        problemas.append(problema(
            "data", "formatos de data misturados (AAAA-MM-DD e DD/MM/AAAA)",
            min(len(iso_ok), len(barra_ok)),
            [f"{len(iso_ok)} linhas ISO, {len(barra_ok)} linhas com barra"]))
    if mistura_dm_md:
        problemas.append(problema(
            "data", "convenções DD/MM e MM/DD misturadas", 1,
            ["há datas com dia>12 na 1ª e na 2ª posição"]))
    elif barra and not (ev_dm or ev_md):
        amb = [i for i in barra if pares[i][0] <= 12 and pares[i][1] <= 12
               and pares[i][0] != pares[i][1]]
        if amb:
            avisos.append(problema(
                "data", "datas ambíguas (DD/MM ou MM/DD); assumido DD/MM/AAAA",
                len(amb), (ex_linha(i, serie[i]) for i in amb)))


def checar_numericas(df: pd.DataFrame, cols: list, problemas: list, avisos: list):
    for col in cols:
        serie = df[col]
        parsed = {}
        nao_num, fora_padrao, negativos, zeros, nao_int = [], [], [], [], []
        for i, v in serie.items():
            if eh_nulo(v):
                continue
            x = parse_num(v)
            if x is None:
                nao_num.append(i)
                continue
            parsed[i] = x
            if not RE_NUM_PADRAO.match(v.strip()):
                fora_padrao.append(i)
            if x < 0:
                negativos.append(i)
            elif x == 0 and col in ("quantidade", "preco_unitario"):
                zeros.append(i)
            if col == "quantidade" and x != int(x):
                nao_int.append(i)
        for lista, tipo in ((nao_num, "valor não numérico"),
                            (fora_padrao, "formato numérico fora do padrão (R$, vírgula ou separador de milhar)"),
                            (negativos, "valor negativo"),
                            (zeros, "valor zero"),
                            (nao_int, "quantidade não inteira")):
            if lista:
                problemas.append(problema(col, tipo, len(lista),
                                          (ex_linha(i, serie[i]) for i in lista)))
        # valores atípicos (aviso): só quantidade (global) e preco_unitario (dentro
        # do mesmo produto). valor_total é coberto pela checagem de quantidade×preço.
        if col == "quantidade":
            grupos = {"": [i for i, x in parsed.items() if x > 0]}
        elif col == "preco_unitario" and "produto" in df.columns:
            grupos = {}
            for i, x in parsed.items():
                if x > 0:
                    grupos.setdefault(chave(df.at[i, "produto"]), []).append(i)
        else:
            continue
        atip = []
        for idxs in grupos.values():
            pos = pd.Series({i: parsed[i] for i in idxs})
            if len(pos) < 20:
                continue
            q1, q3 = pos.quantile(0.25), pos.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                atip += [i for i, x in pos.items()
                         if x > q3 + K_IQR * iqr or x < q1 - K_IQR * iqr]
        if atip:
            avisos.append(problema(
                col, f"valor atípico (fora de {K_IQR:g}×IQR)", len(atip),
                (ex_linha(i, serie[i]) for i in sorted(atip))))


def checar_valor_total(df: pd.DataFrame, problemas: list) -> None:
    div = []
    for i in df.index:
        q, p, t = (parse_num(df.at[i, c]) for c in NUMERICAS)
        if None in (q, p, t):
            continue
        if abs(q * p - t) > TOLERANCIA:
            div.append((i, q, p, t))
    if div:
        problemas.append(problema(
            "valor_total", "valor_total diferente de quantidade × preco_unitario",
            len(div), (f"linha {i + 2}: {q:g}×{p:g}={q * p:.2f}, valor_total={t:g}"
                       for i, q, p, t in div)))


def checar_duplicatas(df: pd.DataFrame, problemas: list) -> None:
    norm = df.apply(lambda c: c.str.strip())
    dup = norm.duplicated(keep="first")
    if dup.any():
        primeira = {}
        for i, tup in enumerate(map(tuple, norm.itertuples(index=False))):
            primeira.setdefault(tup, i)
        exemplos = [f"linha {i + 2} repete a linha {primeira[tuple(norm.iloc[i])] + 2}"
                    for i in df.index[dup]]
        problemas.append(problema("(linha inteira)",
                                  "linha duplicada (cópia exata de outra)",
                                  dup.sum(), exemplos))
    if "pedido_id" in df.columns:
        resto = norm[~dup]
        ids = resto["pedido_id"]
        rep = resto[(~ids.map(eh_nulo)) & ids.duplicated(keep="first")]
        if len(rep):
            problemas.append(problema(
                "pedido_id", "pedido_id repetido com conteúdo diferente", len(rep),
                (ex_linha(i, df.at[i, "pedido_id"]) for i in rep.index)))


def checar_categorias(df: pd.DataFrame, cols: list, grafias: list, problemas: list):
    for col in cols:
        grupos: dict[str, Counter] = {}
        linhas: dict[tuple, list] = {}
        for i, v in df[col].items():
            if eh_nulo(v):
                continue
            k = chave(v, regiao=(col == "regiao"))
            grupos.setdefault(k, Counter())[v] += 1
            linhas.setdefault((k, v), []).append(i)
        minoritarias = []
        for k, cont in grupos.items():
            if len(cont) < 2:
                continue
            ordenado = sorted(cont.items(), key=lambda kv: (-kv[1], kv[0]))
            canonica = ordenado[0][0]
            grafias.append({"coluna": col, "canonica": canonica,
                            "variantes": [(v, n) for v, n in ordenado]})
            for v, _ in ordenado[1:]:
                minoritarias += linhas[(k, v)]
        if minoritarias:
            problemas.append(problema(
                col, "categoria escrita de formas diferentes", len(minoritarias),
                (ex_linha(i, df.at[i, col]) for i in sorted(minoritarias))))


def tipo_inferido(serie: pd.Series, col: str) -> str:
    vals = [v for v in serie if not eh_nulo(v)]
    if not vals:
        return "vazio"
    if col == "data":
        return "data"
    nums = [parse_num(v) for v in vals]
    if all(x is not None for x in nums):
        return "inteiro" if all(x == int(x) for x in nums) else "decimal"
    return "texto"


# -------------------------------------------------------------------- análise
def analisar(entrada: Path) -> dict:
    res = {"arquivo": str(entrada), "fatal": None, "linhas": 0, "colunas": [],
           "esperadas_ausentes": [], "extras": [], "problemas": [], "avisos": [],
           "grafias": [], "tipos": {}, "nulos": {}}
    try:
        df = ler(entrada)
    except Exception as e:                       # entrada inexistente/vazia/ilegível
        res["fatal"] = f"{type(e).__name__}: {e}"
        return res

    res["linhas"] = len(df)
    brutas = list(df.columns)
    res["colunas"] = brutas
    mapa = {c: c.strip().lower() for c in brutas}
    df = df.rename(columns=mapa)
    for c in brutas:
        if c != mapa[c] and mapa[c] in COLUNAS:
            res["problemas"].append(problema(
                c, "nome da coluna fora do padrão", 1, [f"esperado: {mapa[c]!r}"]))
    res["esperadas_ausentes"] = [c for c in COLUNAS if c not in df.columns]
    res["extras"] = [c for c in df.columns if c not in COLUNAS]
    for c in res["esperadas_ausentes"]:
        res["problemas"].append(problema(c, "coluna obrigatória ausente", 1,
                                         ["(coluna não encontrada no cabeçalho)"]))
    for c in COLUNAS:
        if c in df.columns:
            res["tipos"][c] = tipo_inferido(df[c], c)
            nulos = [i for i, v in df[c].items() if eh_nulo(v)]
            res["nulos"][c] = len(nulos)
            if nulos:
                res["problemas"].append(problema(
                    c, "valor nulo/vazio", len(nulos),
                    (f"linha {i + 2}" for i in nulos)))

    p, av = res["problemas"], res["avisos"]
    if "data" in df.columns:
        checar_datas(df["data"], p, av)
    checar_numericas(df, [c for c in NUMERICAS if c in df.columns], p, av)
    if all(c in df.columns for c in NUMERICAS):
        checar_valor_total(df, p)
    checar_duplicatas(df, p)
    checar_categorias(df, [c for c in TEXTO if c in df.columns], res["grafias"], p)
    return res


# ------------------------------------------------------------------- relatório
def renderizar(res: dict) -> str:
    L = ["# Relatório de qualidade dos dados", "",
         f"- Arquivo analisado: `{res['arquivo']}`",
         f"- Gerado em: {datetime.now():%Y-%m-%d %H:%M}",
         "- Gerado por: `validar_planilha.py` (pandas). Todas as contagens vêm do código."]
    if res["fatal"]:
        L += ["", "## Resultado: ERRO NA ENTRADA", "",
              f"Não foi possível validar a planilha: **{esc(res['fatal'])}**", "",
              "Nenhuma análise de qualidade foi feita."]
        return "\n".join(L) + "\n"

    probs = res["problemas"]
    total = sum(p["quantidade"] for p in probs)
    L += ["", "## Resultado: " + (
        f"❌ {len(probs)} tipo(s) de problema encontrado(s), {total} ocorrência(s) no total"
        if probs else "✅ Nenhum problema encontrado"), ""]

    L += ["## 1. Estrutura", "",
          f"- Linhas de dados: **{res['linhas']}**",
          f"- Colunas ({len(res['colunas'])}): {', '.join(f'`{c}`' for c in res['colunas'])}"]
    if res["esperadas_ausentes"]:
        L.append("- Colunas obrigatórias ausentes: "
                 + ", ".join(f"`{c}`" for c in res["esperadas_ausentes"]))
    if res["extras"]:
        L.append("- Colunas não previstas: " + ", ".join(f"`{c}`" for c in res["extras"]))
    L += ["", "| Coluna | Tipo inferido | Nulos |", "| --- | --- | --- |"]
    for c, t in res["tipos"].items():
        L.append(f"| `{c}` | {t} | {res['nulos'][c]} |")

    L += ["", "## 2. Problemas encontrados", ""]
    if probs:
        L += ["| Coluna | Tipo de problema | Quantidade | Exemplos |",
              "| --- | --- | ---: | --- |"]
        for p in probs:
            L.append(f"| `{esc(p['coluna'])}` | {esc(p['tipo'])} | {p['quantidade']} | "
                     f"{esc('; '.join(p['exemplos']))} |")
    else:
        L.append("Nenhum problema encontrado.")

    if res["grafias"]:
        L += ["", "## 3. Categorias escritas de formas diferentes", "",
              "A quantidade na tabela de problemas conta as linhas que usam variantes "
              "menos frequentes; a forma mais frequente é sugerida como canônica.", "",
              "| Coluna | Forma mais frequente | Variantes (linhas) |", "| --- | --- | --- |"]
        for g in res["grafias"]:
            var = ", ".join(f"{v!r}×{n}" for v, n in g["variantes"])
            L.append(f"| `{g['coluna']}` | {esc(repr(g['canonica']))} | {esc(var)} |")

    if res["avisos"]:
        L += ["", "## 4. Avisos (não alteram o resultado)", "",
              "| Coluna | Observação | Quantidade | Exemplos |", "| --- | --- | ---: | --- |"]
        for a in res["avisos"]:
            L.append(f"| `{a['coluna']}` | {esc(a['tipo'])} | {a['quantidade']} | "
                     f"{esc('; '.join(a['exemplos']))} |")

    L += ["", "## Método e premissas", "",
          "- Linhas contadas a partir do cabeçalho como linha 1; \"linha N\" é a linha na planilha.",
          "- Nulos: vazio, `NA`, `N/A`, `NaN`, `null`, `None`, `-`, `--`.",
          "- Datas aceitas: `AAAA-MM-DD` e `DD/MM/AAAA`. Com barra, a ordem é deduzida de datas "
          "inequívocas da própria coluna (dia > 12); sem evidência, assume-se DD/MM e há aviso.",
          f"- Valor atípico: acima de Q3+{K_IQR:g}×IQR ou abaixo de Q1−{K_IQR:g}×IQR (aviso; só `quantidade` e `preco_unitario` por produto; mínimo de 20 valores).",
          f"- `valor_total` deve ser igual a `quantidade × preco_unitario` (tolerância {TOLERANCIA}).",
          "- Duplicata = cópia exata de uma linha anterior; a primeira ocorrência não conta. "
          "`pedido_id` repetido só é listado quando o conteúdo da linha difere.",
          "- A planilha original não é modificada."]
    return "\n".join(L) + "\n"


def saida_segura(saida: Path, entrada: Path) -> bool:
    s, pasta = saida.resolve(), entrada.resolve().parent
    return not (s.parent == pasta or pasta in s.parents)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("entrada", nargs="?", type=Path)
    ap.add_argument("-o", "--saida", type=Path, default=Path("saidas/relatorio_qualidade.md"))
    a = ap.parse_args(argv)

    entrada = a.entrada
    if entrada is None:
        entrada = next((p for p in (Path("dados/vendas.csv"), Path("dados/vendas.xlsx"))
                        if p.exists()), Path("dados/vendas.csv"))
    if not saida_segura(a.saida, entrada):
        print(f"ERRO: saída recusada ({a.saida}): não é permitido gravar na pasta da entrada.",
              file=sys.stderr)
        return 4

    res = analisar(entrada)
    a.saida.parent.mkdir(parents=True, exist_ok=True)
    a.saida.write_text(renderizar(res), encoding="utf-8")

    if res["fatal"]:
        print(f"ERRO NA ENTRADA: {res['fatal']}\nRelatório de erro: {a.saida}")
        return 2
    print(f"Linhas: {res['linhas']} | Tipos de problema: {len(res['problemas'])} "
          f"| Avisos: {len(res['avisos'])}")
    for p in res["problemas"][:15]:
        print(f"- {p['coluna']} | {p['tipo']} | {p['quantidade']}")
    if len(res["problemas"]) > 15:
        print(f"... (+{len(res['problemas']) - 15}; veja o relatório)")
    print(f"Relatório: {a.saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
