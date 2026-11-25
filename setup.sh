#!/usr/bin/env bash
# Prepara o ambiente do projeto em Linux/macOS (no Windows, use WSL ou GitHub Codespaces):
#   1. venv Python + requirements.txt
#   2. OpenCode e OpenClaw (+ plugin do Groq para o OpenClaw)
#   3. .env a partir do .env.example (a chave é você quem coloca)
#   4. allowlist de comandos do OpenClaw (python3 e head)
#   5. registro das versões em evidencias/versoes.txt
#
# Uso:  ./setup.sh                  tudo
#       ./setup.sh --sem-opencode   pula o OpenCode
#       ./setup.sh --sem-openclaw   pula o OpenClaw
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$RAIZ"

OPENCODE=1; OPENCLAW=1
for a in "$@"; do
  case "$a" in
    --sem-opencode) OPENCODE=0 ;;
    --sem-openclaw) OPENCLAW=0 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "opção desconhecida: $a" >&2; exit 1 ;;
  esac
done

passo() { echo; echo "==> $*"; }
tem() { command -v "$1" >/dev/null 2>&1; }

# Caminhos onde os instaladores costumam colocar os binários (só acrescenta ao PATH desta sessão)
export PATH="$HOME/.opencode/bin:$HOME/.local/bin:$HOME/.npm-global/bin:$PATH"

# 1. Python ------------------------------------------------------------------
passo "Python e dependências"
tem python3 || { echo "ERRO: instale o Python 3.10 ou mais novo." >&2; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
  || { echo "ERRO: Python 3.10+ necessário (encontrado: $(python3 --version))." >&2; exit 1; }
[[ -d venv ]] || python3 -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "ok: $(python --version), dependências instaladas em venv/"

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

# 3. OpenClaw ----------------------------------------------------------------
if [[ $OPENCLAW -eq 1 ]]; then
  passo "OpenClaw"
  if tem openclaw; then
    echo "já instalado: $(openclaw --version 2>/dev/null | head -1)"
  else
    # O OpenClaw exige Node 24.16+ ou 26.1+. O instalador oficial provisiona o Node se faltar.
    if tem node && node -e 'const [a,b]=process.versions.node.split(".").map(Number);process.exit((a===24&&b>=16)||a>=26?0:1)'; then
      npm install -g openclaw@latest
    else
      curl -fsSL https://openclaw.ai/install.sh | bash
    fi
    hash -r
    tem openclaw || echo "AVISO: openclaw instalado, mas fora do PATH. Abra um terminal novo e rode ./setup.sh de novo."
  fi
  if tem openclaw; then
    echo "plugin do Groq:"
    openclaw plugins install @openclaw/groq-provider || echo "AVISO: falhou (pode já estar instalado)."
    echo "allowlist de comandos (agente main):"
    for bin in "$(command -v python3)" "$(realpath "$(command -v python3)")" "$(command -v head)"; do
      openclaw approvals allowlist add --agent main "$bin" >/dev/null && echo "  + $bin"
    done
  fi
fi

# 4. .env --------------------------------------------------------------------
passo "Chave do Groq"
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "criado .env: edite e coloque sua GROQ_API_KEY (console.groq.com/keys)."
elif grep -q 'sua_chave_aqui' .env; then
  echo "AVISO: .env ainda tem o valor de exemplo; coloque sua chave."
else
  echo "ok: .env já existe (a chave não é exibida)."
fi
grep -qx '.env' .gitignore 2>/dev/null || echo "AVISO: .env não está no .gitignore!"

# 5. versões -----------------------------------------------------------------
passo "Versões"
mkdir -p evidencias
{
  echo "data: $(date -Iseconds)"
  echo "sistema: $(uname -srm)"
  echo "python: $(python --version 2>&1)"
  tem node && echo "node: $(node --version)"
  tem opencode && echo "opencode: $(opencode --version 2>&1 | head -1)"
  tem openclaw && echo "openclaw: $(openclaw --version 2>&1 | head -1)"
} | tee evidencias/versoes.txt

echo
echo "Pronto. Próximos passos:"
echo "  1. coloque a chave no .env"
echo "  2. source venv/bin/activate"
echo "  3. ./run.sh -t tarefa1_validacao -c caso1     (um teste rápido)"
