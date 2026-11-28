#!/usr/bin/env bash
# Prepara o ambiente do projeto em Linux/macOS (no Windows, use WSL ou GitHub Codespaces):
#   1. uv + Python 3.12 + dependências (.venv)
#   2. OpenCode
#   3. Hermes Agent + plugin do Groq, num HERMES_HOME só do projeto (não mexe em ~/.hermes)
#   4. .env a partir do .env.example (a chave só é necessária com PROVEDOR=groq)
#   5. registro das versões em evidencias/versoes.txt
#
# Uso:  ./setup.sh                  tudo
#       ./setup.sh --sem-opencode   pula o OpenCode
#       ./setup.sh --sem-hermes     pula o Hermes
#
# O Ollama não é instalado aqui: instale-o no host (ollama.com) ou use o Docker (ver README).
# O HERMES_HOME do projeto fica em ~/.hermes-av3 (mude com HERMES_HOME_AV3=/outro/caminho).
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$RAIZ"

OPENCODE=1; HERMES=1
for a in "$@"; do
  case "$a" in
    --sem-opencode) OPENCODE=0 ;;
    --sem-hermes) HERMES=0 ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) echo "opção desconhecida: $a" >&2; exit 1 ;;
  esac
done

passo() { echo; echo "==> $*"; }
tem() { command -v "$1" >/dev/null 2>&1; }

# Caminhos onde os instaladores costumam colocar os binários (só acrescenta ao PATH desta sessão)
export PATH="$HOME/.opencode/bin:$HOME/.local/bin:$HOME/.hermes/bin:$PATH"
export HERMES_HOME="${HERMES_HOME_AV3:-$HOME/.hermes-av3}"
HERMES_MIN="0.21.5"   # o plugin do Groq exige esta versão ou mais nova

# 1. Python ------------------------------------------------------------------
passo "uv, Python 3.12 e dependências"
tem uv || curl -LsSf https://astral.sh/uv/install.sh | sh
tem uv || { echo "ERRO: uv instalado, mas fora do PATH. Abra um terminal novo." >&2; exit 1; }
uv sync --frozen   # baixa o Python 3.12 se for preciso
# shellcheck disable=SC1091
source .venv/bin/activate
echo "ok: $(python --version), dependências instaladas em .venv/"

# 2. OpenCode ----------------------------------------------------------------
if [[ $OPENCODE -eq 1 ]]; then
  passo "OpenCode"
  if tem opencode; then
    echo "já instalado: $(opencode --version 2>/dev/null | head -1)"
  else
    curl -fsSL https://opencode.ai/v2/install | bash
    export PATH="$HOME/.opencode/bin:$PATH"
    tem opencode || echo "AVISO: opencode instalado, mas fora do PATH. Abra um terminal novo."
  fi
fi

# 3. Hermes ------------------------------------------------------------------
if [[ $HERMES -eq 1 ]]; then
  passo "Hermes Agent"
  if ! tem hermes; then
    # Instalador oficial; --non-interactive pula o assistente de configuração.
    curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash -s -- --non-interactive
    hash -r
  fi
  if ! tem hermes; then
    echo "AVISO: hermes instalado, mas fora do PATH. Abra um terminal novo e rode ./setup.sh de novo."
  else
    # sem pipe: `hermes --version | head -1` gera broken pipe e, com pipefail, encerra o script
    hv="$(hermes --version 2>&1 || true)"; hv="${hv%%$'\n'*}"
    versao="$(grep -oE '[0-9]+\.[0-9]+\.[0-9]+' <<< "$hv" | head -1 || true)"
    echo "instalado: $hv"
    if [[ "$(printf '%s\n%s\n' "$HERMES_MIN" "$versao" | sort -V | head -1)" != "$HERMES_MIN" ]]; then
      echo "AVISO: Hermes $versao é antigo (mínimo $HERMES_MIN). Atualize com: hermes update"
    fi

    # HERMES_HOME do projeto. O Hermes recusa pasta que outro usuário possa escrever.
    mkdir -p "$HERMES_HOME"; chmod 700 "$HERMES_HOME"
    ( set -a; [[ -f .env ]] && source .env; set +a
      bash scripts/config_hermes.sh "${PROVEDOR:-ollama}" "$HERMES_HOME/config.yaml" )
    echo "HERMES_HOME do projeto: $HERMES_HOME"

    echo "plugin do Groq:"
    if [[ -d "$HERMES_HOME/plugins/groq-provider" ]]; then
      echo "  já instalado"
    else
      hermes plugins install groq-provider || echo "AVISO: falhou instalar o groq-provider."
    fi

    echo "guarda de comandos:"
    python3 scripts/testar_guarda.py | tail -1
  fi
fi

# 4. .env --------------------------------------------------------------------
passo "Arquivo .env"
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "criado .env (padrão: Ollama). Para usar o Groq, defina PROVEDOR=groq e GROQ_API_KEY."
else
  echo "ok: .env já existe (a chave não é exibida)."
fi
grep -qx '.env' .gitignore 2>/dev/null || echo "AVISO: .env não está no .gitignore!"

# 5. versões -----------------------------------------------------------------
passo "Versões"
bash scripts/registrar_versoes.sh

echo
echo "Pronto. Próximos passos:"
echo "  1. com Ollama: ollama pull qwen3:8b   (com Groq: coloque a chave no .env)"
echo "  2. ./run.sh -t tarefa1_validacao -c caso1     (um teste rápido)"
