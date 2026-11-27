#!/usr/bin/env bash
# Roda os casos de teste das tarefas no OpenCode e/ou no Hermes Agent,
# e grava evidências e um CSV de resumo.
# Roda todas as tarefas em uma plataforma antes de passar para a próxima.
#
# Uso:
#   ./run.sh                                   # todas as tarefas, todos os casos, OpenCode e Hermes
#   ./run.sh -t tarefa1_validacao -c caso1     # uma tarefa e um caso
#   ./run.sh -p hermes                         # escolhe as plataformas (opencode, hermes)
#   ./run.sh -p hermes,opencode                # a ordem em -p é a ordem de execução
#   ./run.sh -s 90                             # pausa entre execuções (padrão: 0 com Ollama, 70 com Groq)
#   PROVEDOR=groq ./run.sh                     # usa o Groq em vez do Ollama (padrão)
#   ./run.sh -n                                # só mostra o que faria, sem executar
#
# Para incluir uma tarefa nova, basta criar:
#   prompts/<tarefa>_plataformas.md        instrução enviada ao OpenCode e ao Hermes
#   casos/<tarefa>.txt                     casos de teste: nome | comando de preparo | arquivos esperados
# e liberar os comandos dela em opencode.json e scripts/guarda_hermes.py.
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$RAIZ"

TAREFAS=""; CASOS=""; PLATAFORMAS="opencode,hermes"; PAUSA=""; SECO=0
export HERMES_HOME="${HERMES_HOME_AV3:-$HOME/.hermes-av3}"
export PATH="$HOME/.opencode/bin:$HOME/.local/bin:$HOME/.hermes/bin:$PATH"

while getopts "t:c:p:s:nh" o; do
  case "$o" in
    t) TAREFAS="${OPTARG//,/ }" ;;
    c) CASOS="${OPTARG//,/ }" ;;
    p) PLATAFORMAS="$OPTARG" ;;
    s) PAUSA="$OPTARG" ;;
    n) SECO=1 ;;
    *) sed -n '2,19p' "$0"; exit 0 ;;
  esac
done

# --- ambiente ---------------------------------------------------------------
if [[ -z "${VIRTUAL_ENV:-}" && -f .venv/bin/activate ]]; then source .venv/bin/activate; fi
if [[ -f .env ]]; then
  # o que já veio no ambiente (linha de comando, docker-compose) tem prioridade sobre o .env
  ambiente="$(export -p | grep -E '^declare -x (PROVEDOR|OLLAMA_[A-Z_]+|GROQ_API_KEY|HERMES_TIMEOUT)=' || true)"
  set -a; source .env; set +a
  eval "${ambiente//declare -x/export}"
fi

PROVEDOR="${PROVEDOR:-ollama}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3:8b}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
export OLLAMA_CONTEXT_LENGTH="${OLLAMA_CONTEXT_LENGTH:-65536}"
case "$PROVEDOR" in
  ollama)
    MODELO="$OLLAMA_MODEL"; MODELO_OPENCODE="ollama/$MODELO"
    PAUSA="${PAUSA:-0}"; HERMES_TIMEOUT="${HERMES_TIMEOUT:-600}" ;;   # em CPU o modelo é lento
  groq)
    MODELO="openai/gpt-oss-20b"; MODELO_OPENCODE="groq/$MODELO"
    PAUSA="${PAUSA:-70}"; HERMES_TIMEOUT="${HERMES_TIMEOUT:-300}"
    if [[ ( -z "${GROQ_API_KEY:-}" || "$GROQ_API_KEY" == sua_chave_aqui ) && $SECO -eq 0 ]]; then
      echo "ERRO: GROQ_API_KEY vazia. Copie .env.example para .env e coloque a chave." >&2; exit 1
    fi ;;
  *) echo "ERRO: PROVEDOR desconhecido: $PROVEDOR (use ollama ou groq)" >&2; exit 1 ;;
esac
(( HERMES_TIMEOUT <= 600 )) || { echo "ERRO: HERMES_TIMEOUT não pode passar de 600 s." >&2; exit 1; }

# o Ollama precisa estar no ar e já ter o modelo baixado
if [[ "$PROVEDOR" == ollama && $SECO -eq 0 ]]; then
  tags="$(curl -fsS --max-time 10 "$OLLAMA_BASE_URL/api/tags")" \
    || { echo "ERRO: Ollama não responde em $OLLAMA_BASE_URL." >&2; exit 1; }
  python3 -c 'import json,sys
nomes = {m["name"] for m in json.loads(sys.argv[1]).get("models", [])}
sys.exit(0 if {sys.argv[2], sys.argv[2] + ":latest"} & nomes else 1)' "$tags" "$OLLAMA_MODEL" \
    || { echo "ERRO: modelo $OLLAMA_MODEL não está no Ollama. Rode: ollama pull $OLLAMA_MODEL" >&2; exit 1; }
fi

for p in ${PLATAFORMAS//,/ }; do
  case "$p" in
    opencode|hermes) command -v "$p" >/dev/null || { echo "ERRO: '$p' não encontrado. Rode ./setup.sh." >&2; exit 1; } ;;
    *) echo "ERRO: plataforma desconhecida: $p (use opencode, hermes)" >&2; exit 1 ;;
  esac
done

# HERMES_HOME do projeto: config e chave regravadas a cada execução, para nunca rodar desatualizado.
if [[ ",$PLATAFORMAS," == *",hermes,"* && $SECO -eq 0 ]]; then
  mkdir -p "$HERMES_HOME"; chmod 700 "$HERMES_HOME"
  bash scripts/config_hermes.sh "$PROVEDOR" "$HERMES_HOME/config.yaml" || exit 1
  if [[ "$PROVEDOR" == groq ]]; then
    [[ -d "$HERMES_HOME/plugins/groq-provider" ]] \
      || { echo "ERRO: plugin groq-provider ausente em $HERMES_HOME. Rode ./setup.sh." >&2; exit 1; }
    ( umask 077; printf 'GROQ_API_KEY=%s\n' "$GROQ_API_KEY" > "$HERMES_HOME/.env" )
  else
    rm -f "$HERMES_HOME/.env"   # não deixa a chave do Groq para trás
  fi
fi

if [[ -z "$TAREFAS" ]]; then
  TAREFAS="$(ls casos/tarefa*.txt 2>/dev/null | xargs -n1 basename | sed 's/\.txt$//' | sort | tr '\n' ' ')"
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
CSV="evidencias/resumos/run_${STAMP}.csv"
PRIMEIRA=1

limpar_saidas() { find saidas -mindepth 1 ! -name .gitkeep -exec rm -rf {} + 2>/dev/null; mkdir -p saidas; }

hash_dados() { find dados -type f ! -name .gitkeep -print0 | sort -z | xargs -0 -r sha256sum | sha256sum | cut -d' ' -f1; }

rodar() {  # plataforma prompt_file evid_dir
  local plat="$1" prompt="$2" dir="$3" cod
  case "$plat" in
    opencode)
      # --standalone: servidor próprio, que enxerga o OLLAMA_BASE_URL desta execução
      opencode run --standalone -m "$MODELO_OPENCODE" --format json "$(cat "$prompt")" \
        > "$dir/saida.jsonl" 2> "$dir/stderr.log" ;;
    hermes)
      # --accept-hooks é obrigatório: sem ele, em modo não interativo, o Hermes ignora a guarda
      # de comandos (hooks pre_tool_call) sem avisar. -t terminal: só a ferramenta de shell.
      rm -f "$HERMES_HOME/guarda.jsonl"
      local log="$HERMES_HOME/logs/errors.log" antes_log=0
      [[ -f "$log" ]] && antes_log=$(wc -l < "$log")
      timeout "$HERMES_TIMEOUT" hermes --accept-hooks chat --oneshot -Q \
        --query-file "$prompt" -t terminal --format stream-json \
        > "$dir/saida.jsonl" 2> "$dir/stderr.log"
      cod=$?
      # a sessão continua no gateway mesmo depois do timeout do cliente
      hermes gateway stop -y > "$dir/gateway_stop.log" 2>&1 || echo "  AVISO: falhou ao parar o gateway"
      # trecho do log interno deste caso, sem o ID da organização
      : > "$dir/hermes_errors.log"
      [[ -f "$log" ]] && tail -n +"$((antes_log + 1))" "$log" \
        | sed -E 's/org_[a-z0-9]+/org_***/g' > "$dir/hermes_errors.log"
      mv "$HERMES_HOME/guarda.jsonl" "$dir/guarda.jsonl" 2>/dev/null || : > "$dir/guarda.jsonl"
      return $cod ;;
  esac
}

echo "Execução $STAMP | modelo: $PROVEDOR/$MODELO | tarefas: $TAREFAS | plataformas: $PLATAFORMAS | pausa: ${PAUSA}s"
# Ordem: todas as tarefas e casos em uma plataforma; só depois passa para a próxima.
for plat in ${PLATAFORMAS//,/ }; do
  for tarefa in $TAREFAS; do
    arq_casos="casos/$tarefa.txt"
    prompt="prompts/${tarefa}_plataformas.md"
    [[ -f "$arq_casos" ]] || { echo "AVISO: $arq_casos não existe; pulando $tarefa"; continue; }
    [[ -f "$prompt" ]] || { echo "AVISO: $prompt não existe; pulando $tarefa"; continue; }

    while IFS='|' read -r caso preparo esperados || [[ -n "$caso" ]]; do
      caso="$(echo "$caso" | xargs)"; preparo="$(echo "${preparo:-}" | xargs)"; esperados="$(echo "${esperados:-}" | xargs)"
      [[ -z "$caso" || "$caso" == \#* ]] && continue
      [[ -n "$CASOS" && " $CASOS " != *" $caso "* ]] && continue

      dir="evidencias/$plat/$tarefa/${caso}_${STAMP}"
      echo; echo "== $plat | $tarefa | $caso"
      if [[ $SECO -eq 1 ]]; then echo "  preparo: $preparo"; echo "  evidências: $dir"; continue; fi

      if [[ $PRIMEIRA -eq 0 && "$PAUSA" -gt 0 ]]; then
        echo "  aguardando ${PAUSA}s entre execuções..."; sleep "$PAUSA"
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
      rodar "$plat" "$prompt" "$dir"; codigo=$?
      duracao=$(python3 -c "print(round($(date +%s.%N) - $inicio, 1))")

      [[ "$(hash_dados)" == "$antes" ]] && intactos=1 || intactos=0
      cp -r saidas "$dir/saidas" 2>/dev/null; rm -f "$dir/saidas/.gitkeep"
      python3 scripts/coletar_metricas.py --plataforma "$plat" --tarefa "$tarefa" --caso "$caso" \
        --provedor "$PROVEDOR" --modelo "$MODELO" --dir "$dir" --csv "$CSV" --codigo "$codigo" --duracao "$duracao" \
        --dados-intactos "$intactos" --esperados "$esperados"
    done < "$arq_casos"
  done
done

chmod -R u+w dados 2>/dev/null
if [[ -f "$CSV" ]]; then
  echo; echo "Resumo: $CSV"
  python3 - "$CSV" <<'PY'
import csv, sys
linhas = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
cols = ["plataforma", "modelo", "tarefa", "caso", "concluiu", "saidas_ok", "dados_intactos", "requisicoes", "tokens_entrada", "erros_429", "erros_413", "bloqueios_ou_exec_falho"]
larg = {c: max(len(c), *(len(str(l[c])) for l in linhas)) for c in cols}
print("  ".join(c.ljust(larg[c]) for c in cols))
for l in linhas:
    print("  ".join(str(l[c]).ljust(larg[c]) for c in cols))
PY
fi
