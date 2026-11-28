#!/usr/bin/env python3
"""Testa o script de referência da Tarefa 2 (sem o modelo e sem o Groq).

Para cada caso, gera a planilha sintética numa pasta TEMPORÁRIA (dados/ não é
tocado), roda a Tarefa 1 e a limpeza, e confere com scripts/verificar_limpeza.py
contra o gabarito independente de scripts/gerar_dados_teste.py. Depois testa a
recusa de destinos fora de saidas/ e se o verificador reprova saídas adulteradas.

Uso:    python3 scripts/testar_limpeza.py
Grava:  saidas/testes_limpeza/<caso>/ (relatório, CSV limpo e log de cada caso)
Código de saída: 0 se todos os testes passaram; 1 caso contrário.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PY = sys.executable
SAIDA = RAIZ / "saidas" / "testes_limpeza"

# caso: (código esperado da limpeza, linhas antes, linhas depois, removidas, alteradas)
ESPERADO = {
    "caso1": (0, 505, 497, 8, 0),          # duplicatas e datas inválidas
    "caso2": (0, 500, 499, 1, 10),         # vários problemas nos dados
    "caso3": (2, None, None, None, None),  # arquivo vazio
    "caso4": (0, 500, 500, 0, 0),          # sem erros
}


def rodar(*args) -> subprocess.CompletedProcess:
    return subprocess.run([PY, *map(str, args)], cwd=RAIZ, capture_output=True, text=True,
                          encoding="utf-8")


def hash_pasta(p: Path) -> dict:
    return {str(f.relative_to(p)): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(p.rglob("*")) if f.is_file()} if p.exists() else {}


def main() -> int:
    resultados = []
    antes_dados = hash_pasta(RAIZ / "dados")
    tmp = Path(tempfile.mkdtemp(prefix="tarefa2_"))
    shutil.rmtree(SAIDA, ignore_errors=True)
    try:
        for caso, (rc_esp, n_antes, n_depois, n_rem, n_alt) in ESPERADO.items():
            entrada, gab = tmp / caso, tmp / f"gab_{caso}"
            rodar("scripts/gerar_dados_teste.py", caso, "--destino", entrada, "--gabarito", gab)
            out = SAIDA / caso
            out.mkdir(parents=True, exist_ok=True)
            rel, csv, log = out / "relatorio_qualidade.md", out / "vendas_limpas.csv", out / "log_limpeza.md"
            rodar("scripts/validar_planilha.py", entrada / "vendas.csv", "-o", rel)
            if caso == "caso3":                    # CSV antigo deve ser apagado no erro
                csv.write_text("antigo\n", encoding="utf-8")
            r = rodar("scripts/limpar_vendas.py", entrada / "vendas.csv", "-o", csv,
                      "--log", log, "--relatorio", rel)
            linha1 = (r.stdout or r.stderr).splitlines()[0]
            if rc_esp == 2:
                ok = r.returncode == 2 and not csv.exists() and log.exists()
                resultados.append((caso, ok, f"código {r.returncode}; sem CSV; {linha1}"))
                continue
            esperado = (f"Linhas: antes {n_antes} | removidas {n_rem} | depois {n_depois} | "
                        f"alteradas {n_alt}")
            v = rodar("scripts/verificar_limpeza.py", entrada / "vendas.csv", csv, log,
                      "--gabarito", gab / "vendas_limpas.csv")
            ok = r.returncode == 0 and linha1.startswith(esperado) and v.returncode == 0
            resultados.append((caso, ok, f"{linha1} | {v.stdout.strip().splitlines()[-1]}"))

        # segurança: destinos recusados (código 4) e dados/ intacto
        base = tmp / "caso1" / "vendas.csv"
        for nome, extra in (("saida_em_dados", ["-o", "dados/vendas.csv"]),
                            ("log_em_dados", ["--log", "dados/log_limpeza.md"]),
                            ("saida_na_entrada", ["-o", base]),
                            ("saida_com_..", ["-o", "saidas/../dados/x.csv"]),
                            ("saida_absoluta_fora", ["-o", tmp / "x.csv"])):
            r = rodar("scripts/limpar_vendas.py", base, *extra,
                      *([] if "--log" in extra else ["--log", SAIDA / "seg.md"]))
            resultados.append((f"seg:{nome}", r.returncode == 4, r.stderr.strip()[:90]))

        # o verificador precisa reprovar saídas adulteradas
        c1 = SAIDA / "caso1"
        original = (c1 / "vendas_limpas.csv").read_text(encoding="utf-8")
        linhas = original.splitlines(keepends=True)
        adulteracoes = {
            "silenciosa": "".join(linhas[:1] + [linhas[1].replace(",2400.00", ",2500.00")
                                                .replace(",2,1200.00", ",2,1250.00")] + linhas[2:]),
            "linha_sumida": "".join(linhas[:1] + linhas[2:]),
        }
        for nome, conteudo in adulteracoes.items():
            (c1 / "adulterado.csv").write_text(conteudo, encoding="utf-8")
            v = rodar("scripts/verificar_limpeza.py", tmp / "caso1" / "vendas.csv",
                      c1 / "adulterado.csv", c1 / "log_limpeza.md")
            falhas = [x for x in v.stdout.splitlines() if x.startswith("FALHA")]
            resultados.append((f"verif:{nome}", v.returncode == 1, falhas[0][:90] if falhas else "não reprovou"))
        (c1 / "adulterado.csv").unlink()
        (SAIDA / "seg.md").unlink(missing_ok=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    resultados.append(("dados/ intacto", hash_pasta(RAIZ / "dados") == antes_dados, ""))
    for nome, ok, det in resultados:
        print(f"{'PASSOU' if ok else 'FALHOU'} | {nome} | {det}")
    falhas = sum(not ok for _, ok, _ in resultados)
    print(f"Total: {len(resultados) - falhas}/{len(resultados)} testes passaram")
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
