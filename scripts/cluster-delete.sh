#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/common.sh"

if ! is_true "${DRY_RUN:-0}"; then
  require_command az
  set_azure_subscription
else
  log "DRY_RUN=1: printing Azure delete command without deleting resources"
fi

case "${TEARDOWN_SCOPE:-cluster}" in
  cluster)
    run_cmd az aks delete --resource-group "$RESOURCE_GROUP" --name "$CLUSTER_NAME" --yes --no-wait
    ;;
  resource-group)
    run_cmd az group delete --name "$RESOURCE_GROUP" --yes --no-wait
    ;;
  *)
    die "TEARDOWN_SCOPE must be 'cluster' or 'resource-group', got '${TEARDOWN_SCOPE:-}'"
    ;;
esac
