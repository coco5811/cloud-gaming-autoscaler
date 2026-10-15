# Cloud Gaming Autoscaler - Member 3 Package

This folder contains Member 3's traffic simulation, telemetry collection, experiment runner, and theory notes. It is designed to integrate with the team's `cloud-gaming-autoscaler` repository.

## Contents

- `load_generator/locustfile.py` â€” Locust clients that send simulated player requests to `/join-match` and poll `/status`.
- `load_generator/telemetry_plotter.py` â€” records running/ready Pods and HPA CPU utilization; creates comparison plots.
- `load_generator/run_experiment.sh` â€” runs a fixed-one-replica experiment and an HPA-enabled experiment.
- `load_generator/requirements.txt` â€” Python dependencies.
- `docs/member3_theory.md` â€” theory outline and speaking notes.

## Before running

Confirm with the team that the Deployment is named `game-server`, the Pod label is `app=game-server`, the HPA is named `game-server`, the API accepts the JSON fields in `locustfile.py`, and the service is reachable at `http://localhost:30090`. These are configurable assumptions, not guaranteed facts about the cluster.

Prerequisites: a working Kubernetes cluster, `kubectl` configured for it, the application deployed, Locust/Python dependencies installed, and metrics available if CPU utilization is to be observed.

```bash
cd load_generator
pip install -r requirements.txt
kubectl get nodes
kubectl get deploy,svc,hpa
curl http://localhost:30090/health
curl http://localhost:30090/status
```

## Run experiments

Start with a small test and increase the workload only after confirming the cluster remains responsive:

```bash
./run_experiment.sh unmanaged 20 5 60
./run_experiment.sh managed 20 5 60
```

Arguments are mode, simulated users, spawn rate (users/second), and duration (seconds). The script defaults to `localhost:30090`. Override assumptions with environment variables, for example:

```bash
HOST=http://localhost:30090 DEPLOY=game-server APP_LABEL=game-server HPA_NAME=game-server \
  ./run_experiment.sh managed 100 10 120
```

The script removes only the named HPA in unmanaged mode; verify `HPA_NAME` before running. Managed mode applies the manifest at `../cluster_orchestration/k8s-game-cluster.yaml`, so change `MANIFEST` if the team's filename differs. The script changes cluster resources and should only be run in your team's test namespace/cluster with team approval.

On Windows, run the `.sh` script from Git Bash or WSL. Alternatively, run Locust and the telemetry collector manually from separate terminals.

## Outputs and interpretation

The `results/` directory is created when experiments run. It should contain Locust CSV files, cluster samples, and `comparison.png` after both runs have completed. The graph compares throughput, failure rate, P95 latency, and ready Pod counts. Results are not included in this package because the tests have not been executed against your team's live cluster. Do not invent or claim benchmark outcomes before collecting them.

## Important limitations

- The workload simulates HTTP requests; it is not a real UDP/WebSocket multiplayer protocol implementation.
- The telemetry script reads the first HPA returned by Kubernetes, which may not be the game server's HPA if several HPAs exist. For a valid report, use a dedicated test namespace or update the collector to select the HPA by name/target deployment.
- A PDB alone does not guarantee that active matches survive HPA scale-down. Session-aware draining requires application-level logic and testing; it is not implemented by these files.
- Cloud-cost figures should be labeled illustrative unless based on a selected provider's actual pricing and measured resource usage.
