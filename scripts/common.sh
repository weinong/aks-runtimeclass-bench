#!/usr/bin/env bash
set -Eeuo pipefail

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

is_true() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

print_cmd() {
  printf '+'
  printf ' %q' "$@"
  printf '\n'
}

run_cmd() {
  print_cmd "$@"
  if ! is_true "${DRY_RUN:-0}"; then
    "$@"
  fi
}

append_words() {
  local -n target_array=$1
  local words=${2:-}
  local part
  if [[ -n "$words" ]]; then
    read -r -a parts <<< "$words"
    for part in "${parts[@]}"; do
      target_array+=("$part")
    done
  fi
}

set_azure_subscription() {
  if [[ -n "${AZURE_SUBSCRIPTION:-}" ]]; then
    run_cmd az account set --subscription "$AZURE_SUBSCRIPTION"
  fi
}
