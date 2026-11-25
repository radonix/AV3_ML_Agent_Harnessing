#!/usr/bin/env python3
"""Confere se cada número da resposta final do agente aparece nas saídas das ferramentas.

Uso:
    python3 scripts/checar_numeros.py evidencias/tarefa2_limpeza/caso1

Lê, na pasta de evidências gravada pelo harness:
  - metricas.json  -> campo "final" (a resposta final do modelo)
  - conversa.json  -> mensagens com role "tool" (o que as ferramentas devolveram)

Um número da resposta que não aparece em nenhuma saída de ferramenta é suspeito de ter sido
inventado (ou calculado "de cabeça", o que o prompt proíbe). Datas e valores são quebrados em
partes numéricas (2023-02-01 -> 2023, 2, 1; 25,00 -> 25), então a checagem é por número, não por
texto. Numeração de listas no início da linha ("1)", "2.") é ignorada.

Códigos de saída: 0 = nenhum número sem origem; 1 = há números sem origem; 2 = erro de entrada.
Limite conhecido: um número que apareça por coincidência em alguma saída passa na checagem
(por exemplo, "5" aparece em quase todo log). A conferência é um filtro, não uma prova.
"""
import json
import re
import sys
from pathlib import Path

# vírgula ou ponto só contam como decimal com 1 ou 2 casas ("25,00", "1499.99"); "2,1200" são dois números
NUM = re.compile(r"\d+(?:[.,]\d{1,2}(?!\d))?")
MARCADOR = re.compile(r"^\s*(?:[-*#>]+\s*)*\d+[.)]\s")


def normalizar(token: str) -> str:
    """'25,00' -> '25', '02' -> '2', '2.50' -> '2.5', '505' -> '505'."""
    t = token.replace(",", ".")
    if "." in t:
        inteiro, frac = t.split(".", 1)
        frac = frac.rstrip("0")
        inteiro = inteiro.lstrip("0") or "0"
        return f"{inteiro}.{frac}" if frac else inteiro
    return t.lstrip("0") or "0"


def numeros(texto: str, ignorar_marcadores: bool = False):
    """Devolve [(numero_normalizado, linha)] na ordem em que aparecem."""
    achados = []
    for linha in texto.splitlines():
        trecho = linha
        if ignorar_marcadores:
            m = MARCADOR.match(linha)
            if m:
                trecho = linha[m.end():]
        for tok in NUM.findall(trecho):
            achados.append((normalizar(tok), linha.strip()))
    return achados


def checar(pasta: Path):
    metricas = json.loads((pasta / "metricas.json").read_text(encoding="utf-8"))
    conversa = json.loads((pasta / "conversa.json").read_text(encoding="utf-8"))
    final = metricas.get("final", "")
    if not final.strip():
        return None, [], 0
    saidas = "\n".join(m.get("content") or "" for m in conversa if m.get("role") == "tool")
    conhecidos = {n for n, _ in numeros(saidas)}
    sem_origem, vistos = [], set()
    for n, linha in numeros(final, ignorar_marcadores=True):
        if n not in conhecidos and n not in vistos:
            vistos.add(n)
            sem_origem.append((n, linha))
    total = len({n for n, _ in numeros(final, ignorar_marcadores=True)})
    return True, sem_origem, total


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    pasta = Path(argv[1])
    try:
        ok, sem_origem, total = checar(pasta)
    except FileNotFoundError as e:
        print(f"ERRO: arquivo não encontrado: {e.filename}")
        return 2
    except json.JSONDecodeError as e:
        print(f"ERRO: JSON inválido em {pasta}: {e}")
        return 2
    if ok is None:
        print(f"{pasta}: sem resposta final para conferir (campo 'final' vazio).")
        return 2
    if not sem_origem:
        print(f"OK: os {total} números distintos da resposta final aparecem nas saídas das ferramentas.")
        return 0
    print(f"FALHA: {len(sem_origem)} de {total} números distintos da resposta final não aparecem em nenhuma saída de ferramenta:")
    for n, linha in sem_origem:
        print(f"  {n:>10}  <- {linha[:110]}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
