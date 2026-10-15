# Member 3 — Session Protection update

## Files
- `game_server.py`: tracks individual player sessions, rejects new joins while draining, adds `/leave-match`, `/ready`, and `/drain`.
- `k8s-game-cluster.yaml`: adds readiness/liveness separation, a `preStop` hook, and a 40-second termination grace period.

## Important behavior
1. Kubernetes starts terminating a Pod.
2. The `preStop` hook calls `POST /drain` on that same Pod.
3. `/drain` marks it unready and rejects new joins, then waits up to 25 seconds for active players to leave.
4. The hook sleeps another 3 seconds so readiness changes can propagate.
5. The process then shuts down. The app's shutdown hook makes a final short wait.

## Testing manually
Join:
```bash
curl -X POST http://127.0.0.1:8080/join-match -H "Content-Type: application/json" -d "{\"player_id\":\"player-1\"}"
```

Check active sessions:
```bash
curl http://127.0.0.1:8080/status
```

Leave:
```bash
curl -X POST http://127.0.0.1:8080/leave-match -H "Content-Type: application/json" -d "{\"player_id\":\"player-1\"}"
```

Test draining (use a second terminal to call `/leave-match` while this request waits):
```bash
curl -X POST http://127.0.0.1:8080/drain
```

## Before applying
- Build and load a new `game-lobby:v2` image containing the updated `game_server.py` from the directory containing your Dockerfile. For Minikube, `minikube image build -t game-lobby:v2 .` is a common option. Run it from the correct project directory.
- Confirm your container image includes `/bin/sh` and Python, as the `preStop` hook uses both.
- Apply the YAML only when your team is ready to update the shared cluster.
- Important limitation: sessions are stored in each Pod's memory, but the NodePort Service can route a player's later HTTP request to a different Pod. So this is a useful single-Pod/demo implementation, not complete cross-replica session protection. For reliable multi-replica behavior, add a shared session registry (for example Redis) or real session-affinity/routing so each player's leave/end event reaches the Pod that owns the session. If a Pod crashes or the drain timeout expires with players still active, sessions can still be lost.
- Protect `/drain` with authentication or network restrictions in a real deployment; this demo endpoint is not authenticated.
