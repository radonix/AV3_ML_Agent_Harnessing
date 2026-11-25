#!/usr/bin/env python3
"""Tarefa 2 - Limpeza e padronização da planilha de vendas.

Só LÊ a planilha bruta (e o relatório da Tarefa 1) e só GRAVA dentro de saidas/:
a cópia limpa (CSV) e o log de limpeza (Markdown), com as contagens antes e depois
e a justificativa de cada linha removida ou alterada. Toda decisão e toda contagem
vêm deste código (pandas), nunca do modelo.

Uso:
    python3 scripts/limpar_vendas.py [entrada] [-o saidas/vendas_limpas.csv]
        [--log saidas/log_limpeza.md] [--relatorio saidas/relatorio_qualidade.md]

Sem `entrada`, usa dados/vendas.csv e, se não existir, dados/vendas.xlsx.

Regras fixas (decisões da Tarefa 2; o log repete cada uma):
    R1  Espaços nas pontas e espaços repetidos são removidos de todas as células.
    R2  Duplicata exata (todas as colunas iguais, após R1): fica a 1ª, as demais saem.
    R3  Data: saída em AAAA-MM-DD. Aceita AAAA-MM-DD e DD/MM/AAAA (ordem deduzida da
        coluna, como na Tarefa 1). Data vazia, inexistente ou ilegível: linha removida.
    R4  Números: saída com ponto decimal; quantidade inteira, preço e valor com 2 casas.
        "R$", vírgula decimal e separador de milhar são convertidos.
    R5  Nulos numéricos: falta 1 de (quantidade, preco_unitario, valor_total) -> o valor
        é recomposto pela conta exata (valor = qtd x preço; qtd = valor / preço só se
        der inteiro; preço = valor / qtd). Faltam 2 ou 3 -> linha removida.
    R6  valor_total diferente de quantidade x preco_unitario (tolerância 0,02):
        valor_total é recalculado (quantidade e preço são a fonte).
    R7  Quantidade negativa com preço positivo = DEVOLUÇÃO: mantida, com valor_total
        negativo. Preço negativo ou zero, quantidade zero ou não inteira = ERRO: removida.
    R8  Texto vazio (produto, categoria, regiao, vendedor, pedido_id): preenchido com
        "Não informado" (a venda existiu; não se inventa o valor).
    R9  regiao vira sigla de UF ("São Paulo", "sao paulo", " sp " -> "SP").
        produto, categoria e vendedor: variantes que só diferem em maiúsculas/acentos/
        espaços viram a forma mais frequente.
    R10 Duplicata que só aparece depois da padronização: removida (fica a 1ª).
    R11 Quantidade ou preço atípico (fora de 3xIQR) e pedido_id repetido com conteúdo
        diferente: MANTIDOS e listados no log para revisão humana (não é erro provado).

Códigos de saída:
    0  limpeza concluída (CSV e log gravados)
    2  entrada inexistente, vazia, ilegível ou sem coluna obrigatória (só o log é
       gravado; um vendas_limpas.csv antigo é apagado para não ser usado pela Tarefa 3)
    4  destino recusado (fora de saidas/, igual à entrada ou ao relatório)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validar_planilha import (COLUNAS, K_IQR, NUMERICAS, RE_BARRA, RE_ISO,  # noqa: E402
                              RE_NUM_PADRAO, TOLERANCIA, UFS, chave, eh_nulo, esc, ler,
                              parse_data_iso, parse_num)

RAIZ = Path(__file__).resolve().parents[1]
PASTA_SAIDAS = RAIZ / "saidas"
NAO_INFORMADO = "Não informado"
TEXTO_PADRONIZAVEL = ["produto", "categoria", "vendedor"]
TEXTO_PREENCHIVEL = ["pedido_id", "produto", "categoria", "regiao", "vendedor"]
SIGLA_POR_NOME = {nome: sigla.upper() for sigla, nome in UFS.items()}

REGRAS = [
    "**R1 Espaços:** espaços nas pontas e repetidos são removidos de todas as células.",
    "**R2 Duplicatas exatas:** linhas idênticas em todas as colunas (após R1); fica a primeira.",
    "**R3 Datas:** formato final `AAAA-MM-DD`. `DD/MM/AAAA` é convertido (ordem deduzida "
    "da própria coluna, como na Tarefa 1). Data vazia, inexistente ou ilegível: **linha removida**, "
    "porque não há como saber o mês da venda.",
    "**R4 Números:** ponto como separador decimal; `quantidade` inteira; `preco_unitario` e "
    "`valor_total` com 2 casas. `R$`, vírgula decimal e separador de milhar são convertidos.",
    "**R5 Nulos numéricos:** se falta só um entre `quantidade`, `preco_unitario` e `valor_total`, "
    "ele é recomposto pela conta exata (`valor_total = quantidade × preco_unitario`; "
    "`quantidade = valor_total ÷ preco_unitario` só se o resultado for inteiro). "
    "Se faltam dois ou três: **linha removida**.",
    f"**R6 valor_total divergente** de `quantidade × preco_unitario` (tolerância {TOLERANCIA}): "
    "`valor_total` é **recalculado**; quantidade e preço são tratados como a fonte.",
    "**R7 Negativos:** `quantidade` negativa com preço positivo é **devolução** e é mantida "
    "(com `valor_total` negativo). `preco_unitario` negativo ou zero, `quantidade` zero ou não "
    "inteira são **erro**: linha removida.",
    f"**R8 Texto vazio** (`pedido_id`, `produto`, `categoria`, `regiao`, `vendedor`): preenchido "
    f"com `{NAO_INFORMADO}`. A venda é mantida porque a receita existe; o valor não é inventado.",
    "**R9 Padronização:** `regiao` vira a sigla da UF (tabela abaixo). Em `produto`, `categoria` "
    "e `vendedor`, variantes que só diferem em maiúsculas, acentos ou espaços viram a forma mais "
    "frequente.",
    "**R10 Duplicata após padronização:** linhas que ficam idênticas depois de R1–R9; fica a primeira.",
    f"**R11 Revisão humana:** quantidade ou preço atípico (fora de {K_IQR:g}×IQR) e `pedido_id` "
    "repetido com conteúdo diferente **não são alterados nem removidos**; ficam listados na "
    "seção 8 para revisão.",
]

TRATAMENTO_T1 = [   # (trecho do tipo de problema na Tarefa 1, tratamento aplicado)
    ("nome da coluna", "nome normalizado (minúsculas, sem espaços)"),
    ("coluna obrigatória ausente", "limpeza interrompida (código 2)"),
    ("data inválida", "R3: linha removida"),
    ("formatos de data", "R3: convertido para AAAA-MM-DD"),
    ("convenções", "R3: datas ambíguas removidas; as demais convertidas"),
    ("não numérico", "tratado como vazio (R5)"),
    ("fora do padrão", "R4: convertido para número com ponto decimal"),
    ("valor zero", "R7: linha removida"),
    ("não inteira", "R7: linha removida"),
    ("diferente de quantidade", "R6: valor_total recalculado"),
    ("linha duplicada", "R2: linha removida"),
    ("pedido_id repetido", "R10 se ficar idêntica após padronizar; senão R11 (mantida, revisão)"),
    ("formas diferentes", "R9: padronizado"),
]


# ------------------------------------------------------------------- utilidades
def espacos(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).strip())


def fmt_num(x: float, casas: int) -> str:
    v = round(x, casas) + 0.0              # + 0.0 evita "-0.00"
    return f"{int(v)}" if casas == 0 else f"{v:.{casas}f}"


def tratamento(coluna: str, tipo: str) -> str:
    if tipo == "valor nulo/vazio":
        if coluna == "data":
            return "R3: linha removida"
        if coluna in NUMERICAS:
            return "R5: recomposto pela conta ou linha removida"
        return f"R8: preenchido com '{NAO_INFORMADO}'"
    if tipo == "valor negativo":
        return {"quantidade": "R7: devolução mantida",
                "preco_unitario": "R7: linha removida"}.get(
                    coluna, "R7: segue a linha (devolução mantida ou linha removida)")
    for trecho, trat in TRATAMENTO_T1:
        if trecho in tipo:
            return trat
    return "sem regra específica (ver seções 6 a 8)"


def ler_relatorio_t1(caminho: Path) -> dict:
    """Extrai do relatório da Tarefa 1 o nº de linhas e a tabela de problemas."""
    info = {"existe": caminho.exists(), "linhas": None, "arquivo": None, "problemas": [],
            "erro_entrada": False}
    if not info["existe"]:
        return info
    texto = caminho.read_text(encoding="utf-8")
    m = re.search(r"Linhas de dados: \*\*(\d+)\*\*", texto)
    info["linhas"] = int(m[1]) if m else None
    m = re.search(r"Arquivo analisado: `([^`]*)`", texto)
    info["arquivo"] = m[1] if m else None
    info["erro_entrada"] = "ERRO NA ENTRADA" in texto
    secao = texto.split("## 2. Problemas encontrados", 1)[-1].split("\n## ", 1)[0]
    for lin in secao.splitlines():
        m = re.match(r"^\| `(.+?)` \| (.+?) \| (\d+) \|", lin)
        if m:
            info["problemas"].append((m[1], m[2].replace("\\|", "|"), int(m[3])))
    return info


def destino_seguro(alvo: Path, entrada: Path, *proibidos: Path) -> str | None:
    """Devolve o motivo da recusa, ou None se o destino é aceito."""
    a = alvo.resolve()
    if PASTA_SAIDAS.resolve() not in a.parents:
        return "só é permitido gravar dentro de saidas/"
    if a == entrada.resolve() or a in {p.resolve() for p in proibidos}:
        return "o destino é a própria entrada ou o relatório da Tarefa 1"
    return None


# ------------------------------------------------------------------------ datas
def converter_datas(serie: pd.Series) -> tuple[dict, list]:
    """{índice: (data ISO ou None, motivo da remoção ou None)} e avisos."""
    res, barra, avisos = {}, {}, []
    for i, v in serie.items():
        s = v.strip()
        if eh_nulo(s):
            res[i] = (None, "data vazia")
        elif RE_ISO.match(s):
            d = parse_data_iso(s)
            res[i] = (d.isoformat(), None) if d else (None, f"data inexistente ({s!r})")
        elif RE_BARRA.match(s):
            a, b, y = (int(x) for x in RE_BARRA.match(s).groups())
            barra[i] = (a, b, y)
        else:
            res[i] = (None, f"data ilegível ({s!r})")

    ev_dm = any(a > 12 for a, _, _ in barra.values())
    ev_md = any(b > 12 for _, b, _ in barra.values())
    misto = ev_dm and ev_md
    ordem = "md" if (ev_md and not ev_dm) else "dm"

    def criar(y, m, d):
        try:
            return date(y, m, d)
        except ValueError:
            return None

    ambiguas = 0
    for i, (a, b, y) in barra.items():
        original = serie[i].strip()
        dm, md = criar(y, b, a), criar(y, a, b)
        if misto:
            if dm and md and dm != md:
                res[i] = (None, f"data ambígua ({original!r}) numa coluna com DD/MM e MM/DD")
                continue
            d = dm or md
        else:
            d = dm if ordem == "dm" else md
            if d and not (ev_dm or ev_md) and a != b and a <= 12 and b <= 12:
                ambiguas += 1
        res[i] = (d.isoformat(), None) if d else (None, f"data inexistente ({original!r})")
    if barra:
        avisos.append(f"Datas com barra interpretadas como "
                      f"{'MM/DD/AAAA' if ordem == 'md' and not misto else 'DD/MM/AAAA'}"
                      + (" (as duas convenções aparecem; as ambíguas foram removidas)" if misto else "")
                      + ".")
    if ambiguas:
        avisos.append(f"{ambiguas} data(s) ambígua(s) sem evidência na coluna; assumido DD/MM/AAAA.")
    return res, avisos


# ----------------------------------------------------------------------- números
def numeros(q_raw: str, p_raw: str, t_raw: str):
    """Aplica R4–R7 a uma linha. Devolve (q, p, t, alteracoes, motivo_remocao, obs)."""
    alt, obs = [], []
    vals, falta = {}, []
    for col, raw in (("quantidade", q_raw), ("preco_unitario", p_raw), ("valor_total", t_raw)):
        s = raw.strip()
        if eh_nulo(s):
            falta.append(col)
            continue
        x = parse_num(s)
        if x is None:
            falta.append(col)
            obs.append(f"{col} não numérico ({s!r}) tratado como vazio")
            continue
        vals[col] = x
        if not RE_NUM_PADRAO.match(s):
            alt.append(("formato numérico convertido", f"{col}: {s!r} → {x:g}"))

    if len(falta) >= 2:
        return None, None, None, alt, ("valores insuficientes para recompor a venda",
                                       "faltam " + " e ".join(falta)), obs
    q, p, t = vals.get("quantidade"), vals.get("preco_unitario"), vals.get("valor_total")

    if p is not None and p <= 0:
        return None, None, None, alt, ("preco_unitario negativo ou zero (erro)",
                                       f"preco_unitario = {p:g}"), obs
    if q is not None and q != int(q):
        return None, None, None, alt, ("quantidade não inteira (erro)", f"quantidade = {q:g}"), obs
    if q is not None and q == 0:
        return None, None, None, alt, ("quantidade zero (erro)", "quantidade = 0"), obs

    if "valor_total" in falta:
        t = round(q * p, 2)
        alt.append(("valor_total vazio recalculado", f"valor_total: vazio → {t:.2f} ({q:g}×{p:g})"))
    elif "quantidade" in falta:
        qd = t / p
        if abs(qd - round(qd)) > 1e-6 or round(qd) == 0:
            return None, None, None, alt, ("quantidade vazia e não dedutível",
                                           f"valor_total ÷ preço = {qd:.4f} não é inteiro"), obs
        q = float(round(qd))
        alt.append(("quantidade vazia deduzida", f"quantidade: vazio → {q:g} ({t:g}÷{p:g})"))
    elif "preco_unitario" in falta:
        pd_ = round(t / q, 2)
        if pd_ <= 0 or abs(q * pd_ - t) > TOLERANCIA:
            return None, None, None, alt, ("preco_unitario vazio e não dedutível",
                                           f"valor_total ÷ quantidade = {t / q:.4f}"), obs
        p = pd_
        alt.append(("preco_unitario vazio deduzido", f"preco_unitario: vazio → {p:.2f} ({t:g}÷{q:g})"))
    elif abs(q * p - t) > TOLERANCIA:
        novo = round(q * p, 2)
        alt.append(("valor_total divergente recalculado",
                    f"valor_total: {t:g} → {novo:.2f} ({q:g}×{p:g})"))
        t = novo
    if q < 0:
        obs.append("devolução (quantidade negativa), mantida com valor_total negativo")
    return q, p, t, alt, None, obs


# ------------------------------------------------------------------------ limpeza
def limpar(df_bruto: pd.DataFrame) -> dict:
    """Aplica R1–R11. Devolve o DataFrame limpo e tudo o que o log precisa."""
    res = {"remocoes": {}, "alteracoes": {}, "observacoes": {}, "avisos": [],
           "equivalencias": Counter(), "colunas_renomeadas": [], "extras": []}

    # nomes de coluna
    mapa = {c: c.strip().lower() for c in df_bruto.columns}
    res["colunas_renomeadas"] = [(c, n) for c, n in mapa.items() if c != n]
    df = df_bruto.rename(columns=mapa)
    res["extras"] = [c for c in df.columns if c not in COLUNAS]
    ausentes = [c for c in COLUNAS if c not in df.columns]
    if ausentes:
        raise ValueError("coluna obrigatória ausente: " + ", ".join(ausentes))
    df = df[COLUNAS + res["extras"]]
    linha = {i: i + 2 for i in df.index}               # linha na planilha (1 = cabeçalho)

    def remover(i, motivo, detalhe):
        res["remocoes"][i] = (motivo, detalhe)

    def alterar(i, tipo, detalhe):
        res["alteracoes"].setdefault(i, []).append((tipo, detalhe))

    # R1 + R2: duplicatas exatas (comparadas sem espaços sobrando)
    norm = df.apply(lambda c: c.map(espacos))
    primeira = {}
    for i, tup in zip(df.index, map(tuple, norm.itertuples(index=False))):
        if tup in primeira:
            remover(i, "duplicata exata", f"igual à linha {linha[primeira[tup]]}")
        else:
            primeira[tup] = i

    # R3: datas (avaliadas nas linhas que restaram)
    vivas = [i for i in df.index if i not in res["remocoes"]]
    datas, avisos = converter_datas(df.loc[vivas, "data"])
    res["avisos"] += avisos

    final = {}
    for i in vivas:
        iso, motivo = datas[i]
        if motivo:
            remover(i, "data vazia ou inválida", motivo)
            continue
        q, p, t, alt, motivo, obs = numeros(*(df.at[i, c] for c in NUMERICAS))
        if motivo:
            remover(i, *motivo)
            continue
        if iso != df.at[i, "data"]:
            alterar(i, "data convertida para AAAA-MM-DD", f"data: {df.at[i, 'data']!r} → {iso}")
        for tipo, det in alt:
            alterar(i, tipo, det)
        for o in obs:
            res["observacoes"].setdefault(i, []).append(o)
        reg = {"data": iso, "quantidade": fmt_num(q, 0), "preco_unitario": fmt_num(p, 2),
               "valor_total": fmt_num(t, 2), "_q": q, "_p": p}
        for c in TEXTO_PREENCHIVEL + res["extras"]:
            reg[c] = espacos(df.at[i, c])
        final[i] = reg

    # R8: texto vazio
    for i, reg in final.items():
        for c in TEXTO_PREENCHIVEL:
            if eh_nulo(reg[c]):
                alterar(i, f"texto vazio preenchido com '{NAO_INFORMADO}'",
                        f"{c}: {df.at[i, c]!r} → {NAO_INFORMADO!r}")
                reg[c] = NAO_INFORMADO

    # R9: região -> sigla; demais textos -> forma mais frequente
    desconhecidas = Counter()
    for i, reg in final.items():
        v = reg["regiao"]
        if v == NAO_INFORMADO:
            continue
        k = chave(v)
        sigla = k.upper() if k in UFS else SIGLA_POR_NOME.get(k)
        if sigla:
            reg["regiao"] = sigla
        else:
            desconhecidas[v] += 1
    if desconhecidas:
        res["avisos"].append("Região sem UF correspondente, mantida como está: "
                             + ", ".join(f"{v!r}×{n}" for v, n in desconhecidas.items()) + ".")
    for c in TEXTO_PADRONIZAVEL:
        grupos: dict[str, Counter] = {}
        for reg in final.values():
            if reg[c] != NAO_INFORMADO:
                grupos.setdefault(chave(reg[c]), Counter())[reg[c]] += 1
        canonica = {k: sorted(cont.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
                    for k, cont in grupos.items()}
        for reg in final.values():
            if reg[c] != NAO_INFORMADO:
                reg[c] = canonica[chave(reg[c])]

    # R10: duplicatas que só aparecem depois de padronizar
    vistos = {}
    for i, reg in list(final.items()):
        tup = tuple(reg[c] for c in COLUNAS + res["extras"])
        if tup in vistos:
            remover(i, "duplicata após padronização", f"igual à linha {linha[vistos[tup]]}")
            del final[i]
            res["alteracoes"].pop(i, None)
            res["observacoes"].pop(i, None)
        else:
            vistos[tup] = i

    # registra alterações de texto (comparando com a célula original)
    for i, reg in final.items():
        for c in TEXTO_PREENCHIVEL + res["extras"]:
            bruto, novo = df.at[i, c], reg[c]
            if bruto == novo or novo == NAO_INFORMADO and eh_nulo(bruto):
                continue
            if espacos(bruto) == novo:
                tipo = "espaços extras removidos"
            elif c == "regiao":
                tipo = "região convertida para sigla de UF"
                res["equivalencias"][(c, espacos(bruto), novo)] += 1
            else:
                tipo = "grafia padronizada"
                res["equivalencias"][(c, espacos(bruto), novo)] += 1
            alterar(i, tipo, f"{c}: {bruto!r} → {novo!r}")

    # R11: só observação (mantidas para revisão humana)
    ids = Counter(reg["pedido_id"] for reg in final.values() if reg["pedido_id"] != NAO_INFORMADO)
    for i, reg in final.items():
        if ids[reg["pedido_id"]] > 1:
            res["observacoes"].setdefault(i, []).append(
                f"pedido_id {reg['pedido_id']!r} repetido com conteúdo diferente (revisar)")

    def atipicos(grupo_por, col_valor, rotulo):
        grupos = {}
        for i, reg in final.items():
            if reg[col_valor] > 0:
                grupos.setdefault(grupo_por(reg), []).append(i)
        for idxs in grupos.values():
            s = pd.Series({i: final[i][col_valor] for i in idxs})
            if len(s) < 20:
                continue
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            if iqr <= 0:
                continue
            for i, x in s.items():
                if x > q3 + K_IQR * iqr or x < q1 - K_IQR * iqr:
                    res["observacoes"].setdefault(i, []).append(
                        f"valor atípico em {rotulo} ({x:g}), mantido para revisão")
    atipicos(lambda r: "", "_q", "quantidade")
    atipicos(lambda r: chave(r["produto"]), "_p", "preco_unitario")

    res["df"] = pd.DataFrame([{c: reg[c] for c in COLUNAS + res["extras"]}
                              for reg in final.values()], columns=COLUNAS + res["extras"])
    res["mantidas_idx"] = list(final.keys())
    res["linha"] = linha
    res["pedido"] = {i: espacos(df.at[i, "pedido_id"]) or "(vazio)" for i in df.index}
    res["antes"] = len(df)
    return res


# --------------------------------------------------------------------------- log
def resumo_numerico(res: dict) -> dict:
    lin = res["linha"]
    por_motivo = Counter(m for m, _ in res["remocoes"].values())
    por_tipo = Counter(t for alts in res["alteracoes"].values() for t in {a for a, _ in alts})
    return {
        "linhas_antes": res["antes"],
        "removidas": len(res["remocoes"]),
        "linhas_depois": len(res["df"]),
        "alteradas": len(res["alteracoes"]),
        "com_observacao": len(res["observacoes"]),
        "remocoes_por_motivo": dict(sorted(por_motivo.items())),
        "alteracoes_por_tipo": dict(sorted(por_tipo.items())),
        "linhas_removidas": sorted(lin[i] for i in res["remocoes"]),
        "linhas_alteradas": sorted(lin[i] for i in res["alteracoes"]),
    }


def renderizar_log(entrada: Path, saida: Path, relatorio: Path, t1: dict,
                   res: dict | None, fatal: str | None, apagado: bool) -> str:
    L = ["# Log de limpeza dos dados", "",
         f"- Arquivo de entrada: `{entrada}` (não é alterado)",
         f"- Arquivo limpo: `{saida}`",
         f"- Relatório de qualidade usado: `{relatorio}`"
         + ("" if t1["existe"] else " (**não encontrado**: rode a Tarefa 1)"),
         f"- Gerado em: {datetime.now():%Y-%m-%d %H:%M}",
         "- Gerado por: `limpar_vendas.py` (pandas). Todas as contagens e correções vêm do código."]
    if fatal:
        L += ["", "## Resultado: ERRO NA ENTRADA", "",
              f"A limpeza não foi feita: **{esc(fatal)}**", "",
              "Nenhum arquivo limpo foi gerado."
              + (f" O `{saida}` de uma execução anterior foi **apagado** para que a Tarefa 3 "
                 "não use dados antigos." if apagado else "")]
        return "\n".join(L) + "\n"

    n = resumo_numerico(res)
    lin, ped = res["linha"], res["pedido"]
    L += ["", "## Resultado", "",
          "| Contagem | Linhas |", "| --- | ---: |",
          f"| Antes (linhas de dados na entrada) | {n['linhas_antes']} |",
          f"| Removidas | {n['removidas']} |",
          f"| Depois (linhas em `{saida.name}`) | {n['linhas_depois']} |",
          f"| Alteradas (mantidas com algum valor corrigido) | {n['alteradas']} |",
          f"| Mantidas com observação para revisão humana | {n['com_observacao']} |", "",
          f"Conferência: {n['linhas_antes']} − {n['removidas']} = "
          f"{n['linhas_antes'] - n['removidas']} "
          + ("✅" if n['linhas_antes'] - n['removidas'] == n['linhas_depois'] else "❌")]
    if res["colunas_renomeadas"]:
        L.append("\nColunas renomeadas: " + ", ".join(f"`{a}` → `{b}`"
                                                     for a, b in res["colunas_renomeadas"]))
    if res["extras"]:
        L.append("\nColunas não previstas, mantidas no fim sem tratamento: "
                 + ", ".join(f"`{c}`" for c in res["extras"]))

    L += ["", "## 1. Regras aplicadas", ""] + [f"- {r}" for r in REGRAS]

    L += ["", "## 2. Remoções por motivo", ""]
    if n["remocoes_por_motivo"]:
        L += ["| Motivo | Linhas |", "| --- | ---: |"]
        L += [f"| {m} | {q} |" for m, q in n["remocoes_por_motivo"].items()]
    else:
        L.append("Nenhuma linha removida.")

    L += ["", "## 3. Alterações por tipo", ""]
    if n["alteracoes_por_tipo"]:
        L += ["Uma linha pode ter mais de um tipo de alteração.", "",
              "| Tipo de alteração | Linhas |", "| --- | ---: |"]
        L += [f"| {t} | {q} |" for t, q in n["alteracoes_por_tipo"].items()]
    else:
        L.append("Nenhuma linha alterada.")

    L += ["", "## 4. Tabela de equivalência aplicada", ""]
    if res["equivalencias"]:
        L += ["| Coluna | Valor original | Valor padronizado | Linhas |", "| --- | --- | --- | ---: |"]
        for (c, de, para), q in sorted(res["equivalencias"].items()):
            L.append(f"| `{c}` | {esc(repr(de))} | {esc(repr(para))} | {q} |")
    else:
        L.append("Nenhuma grafia precisou ser padronizada.")
    L += ["", "Equivalência de regiões usada: sigla ou nome do estado, sem diferença de "
          "maiúsculas, acentos ou espaços → sigla da UF (ex.: `São Paulo`, `sao paulo`, ` sp ` → `SP`)."]

    L += ["", "## 5. Problemas do relatório de qualidade (Tarefa 1) e tratamento", ""]
    if not t1["existe"]:
        L.append("Relatório da Tarefa 1 não encontrado; a limpeza seguiu as regras fixas.")
    else:
        if t1["linhas"] is not None and t1["linhas"] != res["antes"]:
            L += [f"⚠️ O relatório indica {t1['linhas']} linhas, mas a entrada tem {res['antes']}: "
                  "o relatório pode ser de outra planilha. Rode a Tarefa 1 de novo.", ""]
        if t1["problemas"]:
            L += ["| Coluna | Problema na Tarefa 1 | Quantidade | Tratamento nesta limpeza |",
                  "| --- | --- | ---: | --- |"]
            for c, tipo, q in t1["problemas"]:
                L.append(f"| `{esc(c)}` | {esc(tipo)} | {q} | {tratamento(c, tipo)} |")
        else:
            L.append("O relatório da Tarefa 1 não lista problemas.")
        L.append("\nAs contagens desta limpeza (seções 2 e 3) podem ser maiores que as da Tarefa 1: "
                 "duplicatas e grafias que só aparecem depois de padronizar não são vistas lá.")

    L += ["", "## 6. Linhas removidas", ""]
    if res["remocoes"]:
        L += ["| Linha | pedido_id | Motivo | Detalhe |", "| ---: | --- | --- | --- |"]
        for i in sorted(res["remocoes"], key=lambda k: lin[k]):
            m, d = res["remocoes"][i]
            L.append(f"| {lin[i]} | {esc(ped[i])} | {m} | {esc(d)} |")
    else:
        L.append("Nenhuma.")

    L += ["", "## 7. Linhas alteradas", ""]
    if res["alteracoes"]:
        L += ["| Linha | pedido_id | Alterações |", "| ---: | --- | --- |"]
        for i in sorted(res["alteracoes"], key=lambda k: lin[k]):
            L.append(f"| {lin[i]} | {esc(ped[i])} | {esc('; '.join(d for _, d in res['alteracoes'][i]))} |")
    else:
        L.append("Nenhuma.")

    L += ["", "## 8. Linhas mantidas com observação (revisão humana)", ""]
    if res["observacoes"]:
        L += ["| Linha | pedido_id | Observação |", "| ---: | --- | --- |"]
        for i in sorted(res["observacoes"], key=lambda k: lin[k]):
            L.append(f"| {lin[i]} | {esc(ped[i])} | {esc('; '.join(res['observacoes'][i]))} |")
    else:
        L.append("Nenhuma.")

    if res["avisos"]:
        L += ["", "## 9. Avisos", ""] + [f"- {a}" for a in res["avisos"]]

    L += ["", "## Contagens para verificação automática", "",
          "Lidas por `scripts/verificar_limpeza.py`, que confere cada número com os arquivos.", "",
          "```json", json.dumps(n, ensure_ascii=False), "```"]
    return "\n".join(L) + "\n"


# -------------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("entrada", nargs="?", type=Path)
    ap.add_argument("-o", "--saida", type=Path, default=Path("saidas/vendas_limpas.csv"))
    ap.add_argument("--log", type=Path, default=Path("saidas/log_limpeza.md"))
    ap.add_argument("--relatorio", type=Path, default=Path("saidas/relatorio_qualidade.md"))
    a = ap.parse_args(argv)

    entrada = a.entrada or next((p for p in (Path("dados/vendas.csv"), Path("dados/vendas.xlsx"))
                                 if p.exists()), Path("dados/vendas.csv"))
    for alvo, outro in ((a.saida, a.log), (a.log, a.saida)):
        motivo = destino_seguro(alvo, entrada, a.relatorio, outro) if alvo != outro else \
            "CSV e log no mesmo arquivo"
        if motivo:
            print(f"ERRO: destino recusado ({alvo}): {motivo}. Nada foi gravado.", file=sys.stderr)
            return 4

    t1 = ler_relatorio_t1(a.relatorio)
    fatal, res = None, None
    try:
        res = limpar(ler(entrada))
    except Exception as e:                       # entrada inexistente/vazia/ilegível/incompleta
        fatal = f"{type(e).__name__}: {e}"

    apagado = False
    a.log.parent.mkdir(parents=True, exist_ok=True)
    if fatal:
        if a.saida.exists():
            a.saida.unlink()
            apagado = True
        a.log.write_text(renderizar_log(entrada, a.saida, a.relatorio, t1, None, fatal, apagado),
                         encoding="utf-8")
        print(f"ERRO NA ENTRADA: {fatal}\nNenhum CSV gerado"
              + (" (CSV antigo apagado)" if apagado else "") + f". Log: {a.log}")
        return 2

    a.saida.parent.mkdir(parents=True, exist_ok=True)
    res["df"].to_csv(a.saida, index=False, lineterminator="\n", encoding="utf-8")
    a.log.write_text(renderizar_log(entrada, a.saida, a.relatorio, t1, res, None, False),
                     encoding="utf-8")

    n = resumo_numerico(res)
    print(f"Linhas: antes {n['linhas_antes']} | removidas {n['removidas']} | "
          f"depois {n['linhas_depois']} | alteradas {n['alteradas']} | "
          f"com observação {n['com_observacao']}")
    print("Remoções: " + ("; ".join(f"{m} {q}" for m, q in n["remocoes_por_motivo"].items())
                          or "nenhuma"))
    print("Alterações: " + ("; ".join(f"{t} {q}" for t, q in n["alteracoes_por_tipo"].items())
                            or "nenhuma"))
    if not t1["existe"]:
        print(f"Aviso: relatório da Tarefa 1 não encontrado ({a.relatorio}).")
    elif t1["linhas"] is not None and t1["linhas"] != n["linhas_antes"]:
        print(f"Aviso: o relatório da Tarefa 1 tem {t1['linhas']} linhas e a entrada "
              f"{n['linhas_antes']}; rode a Tarefa 1 de novo.")
    print(f"CSV: {a.saida} | Log: {a.log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
