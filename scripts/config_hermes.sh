#!/usr/bin/env bash
# Gera o config.yaml do HERMES_HOME do projeto para o provedor escolhido.
# Uso (da raiz do repositório):  scripts/config_hermes.sh <ollama|groq> <destino>
set -euo pipefail
provedor="$1"; destino="$2"
bloco="hermes/modelo_${provedor}.yaml"
[[ -f "$bloco" ]] || { echo "ERRO: provedor desconhecido: $provedor (use ollama ou groq)" >&2; exit 1; }
sed -e "/__BLOCO_MODELO__/r $bloco" -e "/__BLOCO_MODELO__/d" hermes/config.yaml \
  | sed -e "s#__RAIZ__#$PWD#g" \
        -e "s#__MODELO__#${OLLAMA_MODEL:-qwen3:8b}#g" \
        -e "s#__BASE_URL__#${OLLAMA_BASE_URL:-http://localhost:11434}#g" \
        -e "s#__CONTEXTO__#${OLLAMA_CONTEXT_LENGTH:-65536}#g" \
  > "$destino"
