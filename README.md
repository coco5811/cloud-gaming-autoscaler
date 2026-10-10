# Global Multiplayer Gaming Network

## Project Overview

This project demonstrates how cloud-native technologies can support multiplayer game server workloads. It uses FastAPI to simulate game sessions, Docker to containerize the application, and Kubernetes to deploy and scale game-server instances.

The prototype demonstrates CPU-based horizontal autoscaling under simulated player load.

## Technologies Used

- **Python and FastAPI:** Game-server API and simulated game loop.
- **Docker:** Packages the application into a container image.
- **Kubernetes:** Manages game-server Pods through a Deployment.
- **Minikube:** Runs a local Kubernetes cluster.
- **Kubernetes Service:** Exposes the game server and routes traffic to available Pods.
- **Horizontal Pod Autoscaler (HPA):** Adjusts the number of Pods according to CPU utilization.

## Project Structure

```text
cloud-gaming-autoscaler/
├── README.md
├── game_backend/
│   ├── game_server.py
│   ├── Dockerfile
│   └── requirements.txt
└── cluster_orchestration/
    └── k8s-game-cluster.yaml
```

## Game Server Features

- `GET /health` — checks whether the server is healthy.
- `GET /status` — displays server status, active-player count, tick count, and uptime.
- `POST /join-match` — simulates a player joining a game session.
- Simulated game loop — runs approximately 20 ticks per second.
- Simulated CPU workload — represents processing associated with player activity.

The prototype keeps player counts in each server process's local memory. It does not implement a shared production game-state system.

## Kubernetes Configuration

The Kubernetes configuration defines three resources:

1. **Deployment:** Manages the game-server Pods.
2. **NodePort Service:** Exposes the server on port `30090` at the Kubernetes node level.
3. **Horizontal Pod Autoscaler:** Targets 60% average CPU utilization and scales between 1 and 5 replicas.

The container requests `100m` CPU and has a limit of `250m` CPU.

## Setup and Execution

### 1. Start Docker Desktop

Open Docker Desktop and wait until its engine is running.

### 2. Start Minikube

From the project root in PowerShell:

```powershell
minikube start --driver=docker
```

### 3. Verify the cluster

```powershell
kubectl get nodes
```

The Minikube node should show `Ready`.

### 4. Load the Docker image if necessary

If the image is unavailable inside Minikube, rebuild it from the `game_backend` directory:

```powershell
docker build -t game-lobby:v1 .
minikube image load game-lobby:v1
```

Return to the project root before running the following commands.

### 5. Apply the Kubernetes configuration

```powershell
kubectl apply -f .\cluster_orchestration\k8s-game-cluster.yaml
```

### 6. Verify deployment and autoscaling

```powershell
kubectl get pods -l app=game-server
kubectl get services
kubectl get hpa
kubectl top pods
```

### 7. Expose the service locally

Run:

```powershell
minikube service game-server-service --url
```

Use the URL printed by the command. Keep that terminal open while using the URL.

Open the URL followed by `/health` in a browser to check the server.

### 8. Simulate player requests

Replace the example URL below with the URL printed in the previous step:

```powershell
1..20 | ForEach-Object {
    Invoke-RestMethod `
      -Uri "http://127.0.0.1:55461/join-match" `
      -Method Post `
      -ContentType "application/json" `
      -Body (@{player_id="player$_"} | ConvertTo-Json)
}
```

### 9. Observe autoscaling

After generating load, run:

```powershell
kubectl top pods
kubectl get hpa
kubectl get pods -l app=game-server
```

When CPU utilization remains above the target, the HPA may increase the replica count, up to the configured maximum of five Pods. Scaling takes time and depends on the observed metrics.

## Architecture

Player requests reach the Kubernetes Service, which routes traffic to available game-server Pods. The HPA monitors average CPU utilization and adjusts the Deployment's replica count.

```text
Player / Load Generator
          |
          v
 Kubernetes Service
          |
          v
   Game-server Pods
          ^
          |
    Kubernetes HPA
          |
   Monitors CPU usage
          |
   Scales the Deployment
```

## Current Limitations

- Game state is stored in local process memory rather than shared storage.
- The game loop simulates processing; it is not a complete multiplayer game engine.
- CPU utilization is used for autoscaling instead of custom game-session metrics.
- The prototype does not implement production-grade session migration, persistent connections, or distributed game-state synchronization.

## Future Improvements

- Introduce shared session state and session-aware orchestration.
- Add load testing with Locust.
- Explore custom metrics for active sessions and player counts.
- Investigate production multiplayer networking and graceful session shutdown.

## Team Project

This implementation focuses on game-server execution, containerization, and the foundation for Kubernetes-based scaling within the Global Multiplayer Gaming Network project.