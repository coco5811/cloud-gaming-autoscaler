#!/usr/bin/env bash
# Usage: ./run_experiment.sh unmanaged|managed [users] [spawn_rate] [seconds]
# Run from load_generator/. Requires Bash, kubectl, Locust, Python deps and a running cluster.
set -euo pipefail

MODE=${1:?usage: $0 unmanaged\|managed [users] [spawn_rate] [seconds]}
USERS=${2:-100}
RATE=${3:-10}
DURATION=${4:-60}
HOST=${HOST:-http://localhost:30090}
DEPLOY=${DEPLOY:-game-server}
APP_LABEL=${APP_LABEL:-game-server}
HPA_NAME=${HPA_NAME:-game-server}
MANIFEST=${MANIFEST:-../cluster_orchestration/k8s-game-cluster.yaml}

if [[ "$MODE" != "unmanaged" && "$MODE" != "managed" ]]; then
  echo "Mode must be unmanaged or managed" >&2; exit 2
fi
mkdir -p results

echo ">> Target: $HOST | deployment: $DEPLOY | label: app=$APP_LABEL"
if [[ "$MODE" == "unmanaged" ]]; then
  echo ">> Removing only HPA '$HPA_NAME' and pinning to 1 replica"
  kubectl delete hpa "$HPA_NAME" --ignore-not-found
  kubectl scale deployment "$DEPLOY" --replicas=1
else
  echo ">> Applying manifest and resetting to 1 replica"
  if [[ ! -f "$MANIFEST" ]]; then echo "Manifest not found: $MANIFEST" >&2; exit 1; fi
  kubectl apply -f "$MANIFEST"
  kubectl scale deployment "$DEPLOY" --replicas=1
fi
kubectl rollout status deployment "$DEPLOY" --timeout=120s
echo ">> Allowing cluster to settle for 15 seconds"; sleep 15

echo ">> Starting telemetry collector"
python telemetry_plotter.py collect --app "$APP_LABEL" \
  --out "results/${MODE}_cluster.csv" --duration $((DURATION + 20)) &
COLLECTOR=$!

cleanup() { kill "$COLLECTOR" 2>/dev/null || true; }
trap cleanup EXIT

echo ">> Running $USERS users at spawn rate $RATE for ${DURATION}s"
locust -f locustfile.py --headless -u "$USERS" -r "$RATE" -t "${DURATION}s" \
  --host "$HOST" --csv "results/${MODE}"
wait "$COLLECTOR" || true
trap - EXIT
echo ">> Finished. Results are in load_generator/results/"

if [[ -f results/unmanaged_cluster.csv && -f results/managed_cluster.csv && \
      -f results/unmanaged_stats_history.csv && -f results/managed_stats_history.csv ]]; then
  python telemetry_plotter.py plot \
    --run "Unmanaged (1 pod)" results/unmanaged results/unmanaged_cluster.csv \
    --run "HPA enabled" results/managed results/managed_cluster.csv \
    --out results/comparison.png
fi
