#!/usr/bin/env bash
# Usage: ./run_experiment.sh unmanaged|managed [users] [spawn_rate] [seconds]
# Run from any directory. Requires Bash, kubectl, Locust, Python deps and a running cluster.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE=${1:?usage: $0 unmanaged\|managed [users] [spawn_rate] [seconds]}
USERS=${2:-100}
RATE=${3:-10}
DURATION=${4:-60}
HOST=${HOST:-http://localhost:30090}
DEPLOY=${DEPLOY:-game-server-deployment}
APP_LABEL=${APP_LABEL:-game-server}
HPA_NAME=${HPA_NAME:-game-server-hpa}
MANIFEST=${MANIFEST:-"$SCRIPT_DIR/../cloud_orchestration/k8s-game-cluster.yaml"}

if [[ "$MODE" != "unmanaged" && "$MODE" != "managed" ]]; then
  echo "Mode must be unmanaged or managed" >&2
  exit 2
fi

command -v kubectl >/dev/null || { echo "kubectl is required" >&2; exit 1; }
command -v locust >/dev/null || { echo "Locust is required (pip install -r requirements.txt)" >&2; exit 1; }
command -v python >/dev/null || { echo "Python is required" >&2; exit 1; }

# Check the endpoint before changing HPA or replica state.
if ! curl --connect-timeout 3 --max-time 5 -fsS "${HOST%/}/health" >/dev/null; then
  echo "Cannot reach ${HOST%/}/health." >&2
  echo "For Minikube on Docker Desktop, run 'minikube service game-server-service --url' in another terminal and set HOST to that URL; keep that terminal open." >&2
  exit 1
fi

mkdir -p results
echo ">> Target: $HOST | deployment: $DEPLOY | label: app=$APP_LABEL | HPA: $HPA_NAME"
if [[ "$MODE" == "unmanaged" ]]; then
  echo ">> Removing HPA '$HPA_NAME' and pinning to 1 replica"
  kubectl delete hpa "$HPA_NAME" --ignore-not-found
  kubectl scale deployment "$DEPLOY" --replicas=1
else
  if [[ ! -f "$MANIFEST" ]]; then
    echo "Manifest not found: $MANIFEST" >&2
    exit 1
  fi
  echo ">> Applying manifest: $MANIFEST"
  kubectl apply -f "$MANIFEST"
  kubectl scale deployment "$DEPLOY" --replicas=1
fi

kubectl rollout status "deployment/$DEPLOY" --timeout=120s
echo ">> Allowing cluster to settle for 15 seconds"
sleep 15

echo ">> Starting telemetry collector for Pods with app=$APP_LABEL"
python telemetry_plotter.py collect --app "$APP_LABEL" \
  --out "results/${MODE}_cluster.csv" --duration "$((DURATION + 20))" &
COLLECTOR=$!

cleanup() {
  if [[ -n "${COLLECTOR:-}" ]]; then
    kill "$COLLECTOR" 2>/dev/null || true
    wait "$COLLECTOR" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo ">> Running $USERS simulated clients at spawn rate $RATE for ${DURATION}s"
locust -f locustfile.py --headless -u "$USERS" -r "$RATE" -t "${DURATION}s" \
  --host "$HOST" --csv "results/${MODE}"

wait "$COLLECTOR" || true
COLLECTOR=""
trap - EXIT INT TERM
echo ">> Finished. Results are in $SCRIPT_DIR/results/"

if [[ -f results/unmanaged_cluster.csv && -f results/managed_cluster.csv && \
      -f results/unmanaged_stats_history.csv && -f results/managed_stats_history.csv ]]; then
  python telemetry_plotter.py plot \
    --run "Unmanaged (1 pod)" results/unmanaged results/unmanaged_cluster.csv \
    --run "HPA enabled" results/managed results/managed_cluster.csv \
    --out results/comparison.png
fi
