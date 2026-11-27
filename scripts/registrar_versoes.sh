#!/usr/bin/env bash
# Grava as versões das ferramentas em evidencias/versoes.txt (usado pelo setup.sh e pelo container).
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes-av3}"
tem() { command -v "$1" >/dev/null 2>&1; }
primeira_linha() { local s; s="$("$@" 2>&1 || true)"; echo "${s%%$'\n'*}"; }
mkdir -p evidencias
{
  echo "data: $(date -Iseconds)"
  echo "sistema: $(uname -srm)"
  echo "python: $(python3 --version 2>&1)"
  if tem uv; then echo "uv: $(primeira_linha uv --version)"; fi
  if tem opencode; then echo "opencode: $(primeira_linha opencode --version)"; fi
  if tem hermes; then echo "hermes: $(primeira_linha hermes --version)"; fi
  [[ ! -f "$HERMES_HOME/plugins/groq-provider/plugin.yaml" ]] \
    || echo "groq-provider: $(grep -m1 -E '^version:' "$HERMES_HOME/plugins/groq-provider/plugin.yaml" | awk '{print $2}')"
  ov="$(curl -fsS --max-time 5 "${OLLAMA_BASE_URL:-http://localhost:11434}/api/version" 2>/dev/null || true)"
  if [[ -n "$ov" ]]; then
    echo "ollama: $(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["version"])' "$ov")"
  fi
  echo "provedor: ${PROVEDOR:-ollama}"
  if [[ "${PROVEDOR:-ollama}" == ollama ]]; then echo "modelo: ${OLLAMA_MODEL:-qwen3:8b}"; fi
} | tee evidencias/versoes.txt
