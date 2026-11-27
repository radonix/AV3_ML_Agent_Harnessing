#!/usr/bin/env bash
# Registra as versões usadas na execução e passa os argumentos para o run.sh.
set -euo pipefail
cd /app

simulacao=0
for a in "$@"; do [[ "$a" == -n || "$a" == -h ]] && simulacao=1; done
if [[ $simulacao -eq 0 ]]; then
  HERMES_HOME="$HERMES_HOME_AV3" bash scripts/registrar_versoes.sh
fi

exec ./run.sh "$@"
