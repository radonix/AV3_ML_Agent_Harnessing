#!/usr/bin/env bash
# Roda os casos de teste das tarefas no OpenCode, no OpenClaw e/ou no harness próprio,
# e grava evidências e um CSV de resumo.
#
# Uso:
#   ./run.sh                                   # todas as tarefas, todos os casos, OpenCode e OpenClaw
#   ./run.sh -t tarefa1_validacao -c caso1     # uma tarefa e um caso
#   ./run.sh -p harness,opencode,openclaw      # escolhe as plataformas
#   ./run.sh -s 90                             # pausa entre execuções (segundos), por causa do limite do Groq
#   ./run.sh -n                                # só mostra o que faria, sem executar
#
# Para incluir uma tarefa nova, basta criar:
#   agentes/<tarefa>.py                    configuração do harness (já existente no padrão do projeto)
#   prompts/<tarefa>_plataformas.md        instrução enviada ao OpenCode e ao OpenClaw
#   casos/<tarefa>.txt                     casos de teste: nome | comando de preparo | arquivos esperados
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$RAIZ"

TAREFAS=""; CASOS=""; PLATAFORMAS="opencode,openclaw"; PAUSA=70; SECO=0
OPENCLAW_CONFIG="openclaw/openclaw.json5"; OPENCLAW_TIMEOUT=300

while getopts "t:c:p:s:nh" o; do
  case "$o" in
    t) TAREFAS="${OPTARG//,/ }" ;;
    c) CASOS="${OPTARG//,/ }" ;;
    p) PLATAFORMAS="$OPTARG" ;;
    s) PAUSA="$OPTARG" ;;
    n) SECO=1 ;;
    *) sed -n '2,17p' "$0"; exit 0 ;;
  esac
done

# --- ambiente ---------------------------------------------------------------
if [[ -z "${VIRTUAL_ENV:-}" && -f venv/bin/activate ]]; then source venv/bin/activate; fi
if [[ -f .env ]]; then set -a; source .env; set +a; fi
if [[ -z "${GROQ_API_KEY:-}" && $SECO -eq 0 ]]; then
  echo "ERRO: GROQ_API_KEY vazia. Copie .env.example para .env e coloque a chave." >&2; exit 1
fi

for p in ${PLATAFORMAS//,/ }; do
  case "$p" in
    opencode|openclaw) command -v "$p" >/dev/null || { echo "ERRO: '$p' não encontrado. Rode ./setup.sh." >&2; exit 1; } ;;
    harness) ;;
    *) echo "ERRO: plataforma desconhecida: $p (use harness, opencode, openclaw)" >&2; exit 1 ;;
  esac
done

if [[ -z "$TAREFAS" ]]; then
  TAREFAS="$(ls agentes/tarefa*.py 2>/dev/null | xargs -n1 basename | sed 's/\.py$//' | sort | tr '\n' ' ')"
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
CSV="evidencias/resumos/run_${STAMP}.csv"
PRIMEIRA=1

limpar_saidas() { find saidas -mindepth 1 ! -name .gitkeep -exec rm -rf {} + 2>/dev/null; mkdir -p saidas; }

hash_dados() { find dados -type f ! -name .gitkeep -print0 | sort -z | xargs -0 -r sha256sum | sha256sum | cut -d' ' -f1; }

rodar() {  # plataforma tarefa caso prompt_file evid_dir
  local plat="$1" tarefa="$2" caso="$3" prompt="$4" dir="$5"
  case "$plat" in
    opencode)
      opencode run --format json "$(cat "$prompt")" > "$dir/saida.jsonl" 2> "$dir/stderr.log" ;;
    openclaw)
      openclaw agent exec --message-file "$prompt" --cwd . --config "$OPENCLAW_CONFIG" \
        --json --timeout "$OPENCLAW_TIMEOUT" > "$dir/saida.json" 2> "$dir/stderr.log" ;;
    harness)
      python -m "agentes.$tarefa" --exec "${caso}_${STAMP}" > "$dir/terminal.txt" 2>&1
      local cod=$?
      cp "evidencias/$tarefa/${caso}_${STAMP}/"*.json "$dir/" 2>/dev/null
      return $cod ;;
  esac
}

echo "Execução $STAMP | tarefas: $TAREFAS | plataformas: $PLATAFORMAS | pausa: ${PAUSA}s"
for tarefa in $TAREFAS; do
  arq_casos="casos/$tarefa.txt"
  prompt="prompts/${tarefa}_plataformas.md"
  [[ -f "$arq_casos" ]] || { echo "AVISO: $arq_casos não existe; pulando $tarefa"; continue; }

  while IFS='|' read -r caso preparo esperados || [[ -n "$caso" ]]; do
    caso="$(echo "$caso" | xargs)"; preparo="$(echo "${preparo:-}" | xargs)"; esperados="$(echo "${esperados:-}" | xargs)"
    [[ -z "$caso" || "$caso" == \#* ]] && continue
    [[ -n "$CASOS" && " $CASOS " != *" $caso "* ]] && continue

    for plat in ${PLATAFORMAS//,/ }; do
      if [[ "$plat" != harness && ! -f "$prompt" ]]; then
        echo "AVISO: $prompt não existe; pulando $tarefa/$caso em $plat"; continue
      fi
      dir="evidencias/$plat/$tarefa/${caso}_${STAMP}"
      echo; echo "== $plat | $tarefa | $caso"
      if [[ $SECO -eq 1 ]]; then echo "  preparo: $preparo"; echo "  evidências: $dir"; continue; fi

      if [[ $PRIMEIRA -eq 0 && "$PAUSA" -gt 0 ]]; then
        echo "  aguardando ${PAUSA}s (limite de tokens por minuto do Groq)..."; sleep "$PAUSA"
      fi
      PRIMEIRA=0

      # prepara um estado limpo: saidas/ vazia, dados/ gerados pelo caso e protegidos
      chmod -R u+w dados 2>/dev/null; limpar_saidas
      if [[ -n "$preparo" ]] && ! bash -c "$preparo" > /dev/null; then
        echo "  ERRO no preparo do caso: $preparo"; continue
      fi
      chmod -R a-w dados
      antes="$(hash_dados)"
      mkdir -p "$dir"

      inicio=$(date +%s.%N)
      rodar "$plat" "$tarefa" "$caso" "$prompt" "$dir"; codigo=$?
      duracao=$(python3 -c "print(round($(date +%s.%N) - $inicio, 1))")

      [[ "$(hash_dados)" == "$antes" ]] && intactos=1 || intactos=0
      cp -r saidas "$dir/saidas" 2>/dev/null; rm -f "$dir/saidas/.gitkeep"
      python3 scripts/coletar_metricas.py --plataforma "$plat" --tarefa "$tarefa" --caso "$caso" \
        --dir "$dir" --csv "$CSV" --codigo "$codigo" --duracao "$duracao" \
        --dados-intactos "$intactos" --esperados "$esperados"
    done
  done < "$arq_casos"
done

chmod -R u+w dados 2>/dev/null
if [[ -f "$CSV" ]]; then
  echo; echo "Resumo: $CSV"
  python3 - "$CSV" <<'PY'
import csv, sys
linhas = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
cols = ["plataforma", "tarefa", "caso", "concluiu", "saidas_ok", "dados_intactos", "requisicoes", "tokens_entrada", "erros_429", "erros_413"]
larg = {c: max(len(c), *(len(str(l[c])) for l in linhas)) for c in cols}
print("  ".join(c.ljust(larg[c]) for c in cols))
for l in linhas:
    print("  ".join(str(l[c]).ljust(larg[c]) for c in cols))
PY
fi
