from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncio
import time
import math
import os


app = FastAPI(
    title="Global Multiplayer Gaming Server",
    description="Simulated multiplayer game session server",
    version="1.1"
)


# --------------------------------------------------
# GAME SESSION STATE
# --------------------------------------------------

active_sessions = set()
total_join_requests = 0
tick_count = 0
draining = False

server_start_time = time.time()
last_tick_time = time.time()
session_lock = asyncio.Lock()
game_loop_task = None
DRAIN_TIMEOUT_SECONDS = int(os.getenv("DRAIN_TIMEOUT_SECONDS", "25"))


# --------------------------------------------------
# PLAYER REQUEST MODEL
# --------------------------------------------------

class PlayerSession(BaseModel):
    player_id: str = "anonymous"


# --------------------------------------------------
# SIMULATED GAME CPU WORK
# --------------------------------------------------

def simulate_player_processing(player_number: int):
    result = 0.0

    for i in range(5000):
        result += math.sin(i + player_number) * math.cos(i)

    return result


# --------------------------------------------------
# GAME LOOP
# --------------------------------------------------

async def game_loop():
    global tick_count
    global last_tick_time

    while True:
        tick_start = time.time()
        player_count = len(active_sessions)

        for player in range(player_count):
            simulate_player_processing(player)

        tick_count += 1
        last_tick_time = time.time()

        elapsed = time.time() - tick_start
        await asyncio.sleep(max(0, 0.05 - elapsed))


# --------------------------------------------------
# START AND STOP
# --------------------------------------------------

@app.on_event("startup")
async def startup_event():
    global game_loop_task
    game_loop_task = asyncio.create_task(game_loop())


@app.on_event("shutdown")
async def shutdown_event():
    global draining
    draining = True

    deadline = time.monotonic() + 5
    while active_sessions and time.monotonic() < deadline:
        await asyncio.sleep(0.25)

    if game_loop_task is not None:
        game_loop_task.cancel()
        try:
            await game_loop_task
        except asyncio.CancelledError:
            pass


# --------------------------------------------------
# HEALTH AND READINESS
# --------------------------------------------------

@app.get("/health")
async def health_check():
    # Liveness: keep returning healthy while this process is alive.
    return {"status": "healthy", "server": "game-lobby"}


@app.get("/ready")
async def readiness_check():
    # Readiness: a draining Pod must not receive new traffic.
    if draining:
        return JSONResponse(
            status_code=503,
            content={"status": "draining", "ready": False}
        )

    return {"status": "ready", "ready": True}


# --------------------------------------------------
# SERVER STATUS
# --------------------------------------------------

@app.get("/status")
async def server_status():
    uptime = time.time() - server_start_time

    return {
        "status": "draining" if draining else "running",
        "ready": not draining,
        "active_players": len(active_sessions),
        "active_player_ids": sorted(active_sessions),
        "total_join_requests": total_join_requests,
        "tick_count": tick_count,
        "uptime_seconds": round(uptime, 2),
        "tick_rate_hz": 20
    }


# --------------------------------------------------
# JOIN MATCH
# --------------------------------------------------

@app.post("/join-match")
async def join_match(player: PlayerSession):
    global total_join_requests

    async with session_lock:
        if draining:
            raise HTTPException(
                status_code=503,
                detail="This server is draining and is not accepting new players."
            )

        if player.player_id in active_sessions:
            return {
                "message": "Player already has an active session",
                "player_id": player.player_id,
                "active_players": len(active_sessions),
                "server": os.getenv("HOSTNAME", "local-game-server")
            }

        active_sessions.add(player.player_id)
        total_join_requests += 1
        player_count = len(active_sessions)

    simulate_player_processing(player_count)

    return {
        "message": "Player joined the game session",
        "player_id": player.player_id,
        "active_players": len(active_sessions),
        "server": os.getenv("HOSTNAME", "local-game-server")
    }


# --------------------------------------------------
# LEAVE MATCH
# --------------------------------------------------

@app.post("/leave-match")
async def leave_match(player: PlayerSession):
    async with session_lock:
        if player.player_id not in active_sessions:
            raise HTTPException(
                status_code=404,
                detail="No active session found for this player."
            )

        active_sessions.remove(player.player_id)
        remaining_players = len(active_sessions)

    return {
        "message": "Player left the game session",
        "player_id": player.player_id,
        "active_players": remaining_players
    }


# --------------------------------------------------
# GRACEFUL DRAIN
# --------------------------------------------------

@app.post("/drain")
async def drain_server():
    global draining

    # Mark the Pod unready immediately. New joins are rejected from now on.
    draining = True
    deadline = time.monotonic() + DRAIN_TIMEOUT_SECONDS

    while active_sessions and time.monotonic() < deadline:
        await asyncio.sleep(0.25)

    remaining = len(active_sessions)

    return {
        "status": "drained" if remaining == 0 else "drain_timeout",
        "draining": True,
        "active_players_remaining": remaining,
        "timeout_seconds": DRAIN_TIMEOUT_SECONDS
    }
