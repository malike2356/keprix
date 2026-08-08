#!/usr/bin/env bash
# Curl examples for Keprix Universal Sidecar (local loopback).
# Usage: export TOKEN=... PROJECT=demo BASE=http://127.0.0.1:3360
#        bash collection.sh [health|capabilities|session|invoke|jobs|events|approval]

set -euo pipefail

BASE="${BASE:-http://127.0.0.1:3360}"
PROJECT="${PROJECT:-demo}"
TOKEN="${TOKEN:-}"
PREFIX="${BASE}/sidecar/v1"

if [[ -z "${TOKEN}" ]]; then
  echo "Set TOKEN to a bearer workload or demo token" >&2
  exit 1
fi

auth=(-H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" -H "X-Correlation-Id: curl-collection")

cmd="${1:-health}"

case "${cmd}" in
  health)
    curl -fsS "${auth[@]}" "${PREFIX}/projects/${PROJECT}/health" | jq .
    ;;
  capabilities)
    curl -fsS "${auth[@]}" "${PREFIX}/projects/${PROJECT}/capabilities" | jq .
    ;;
  pair)
    : "${PAIRING_CODE:?set PAIRING_CODE}"
    curl -fsS "${auth[@]}" -X POST "${PREFIX}/pair/bootstrap" \
      -d "{\"pairing_code\":\"${PAIRING_CODE}\",\"project_key\":\"${PROJECT}\",\"deployment\":\"local-dev\",\"environment\":\"local\"}" | jq .
    ;;
  session)
    curl -fsS "${auth[@]}" -X POST "${PREFIX}/projects/${PROJECT}/sessions" \
      -d '{"purpose":"demo","tenant_id":"t1","actor_id":"u1"}' | jq .
    ;;
  invoke)
    curl -fsS "${auth[@]}" -X POST "${PREFIX}/projects/${PROJECT}/invoke" \
      -d '{"node":"summarise","purpose":"demo","input":{"text":"hello from curl"}}' | jq .
    ;;
  jobs)
    curl -fsS "${auth[@]}" -X POST "${PREFIX}/projects/${PROJECT}/jobs" \
      -d '{"node":"summarise","purpose":"demo-job","input":{"text":"async hello"}}' | jq .
    ;;
  job-get)
    : "${JOB_ID:?set JOB_ID}"
    curl -fsS "${auth[@]}" "${PREFIX}/projects/${PROJECT}/jobs/${JOB_ID}" | jq .
    ;;
  cancel)
    : "${JOB_ID:?set JOB_ID}"
    curl -fsS "${auth[@]}" -X POST "${PREFIX}/projects/${PROJECT}/jobs/${JOB_ID}/cancel" -d '{}' | jq .
    ;;
  events)
    curl -fsS "${auth[@]}" -X POST "${PREFIX}/projects/${PROJECT}/events" \
      -d '{"id":"evt-1","type":"demo.order.created","source":"curl","data":{"order_id":"ord_1001"}}' | jq .
    ;;
  stream)
    curl -NS "${auth[@]}" "${PREFIX}/projects/${PROJECT}/events/stream"
    ;;
  approval)
    : "${APPROVAL_ID:?set APPROVAL_ID}"
    curl -fsS "${auth[@]}" -X POST "${PREFIX}/projects/${PROJECT}/approvals/${APPROVAL_ID}/decision" \
      -d '{"decision":"approve","actor_id":"u1"}' | jq .
    ;;
  connector-test)
    curl -fsS "${auth[@]}" -X POST "${PREFIX}/projects/${PROJECT}/connectors/order.get/test" \
      -d '{"path_params":{"id":"ord_1001"}}' | jq .
    ;;
  *)
    echo "Unknown command: ${cmd}" >&2
    exit 1
    ;;
esac
