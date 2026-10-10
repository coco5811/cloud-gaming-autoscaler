from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
import time
import math
import os


app = FastAPI(
    title="Global Multiplayer Gaming Server",
    description="Simulated multiplayer game session server",
    version="1.0"
)


# --------------------------------------------------
# GAME SESSION STATE
# --------------------------------------------------

active_players = 0
total_join_requests = 0
tick_count = 0

server_start_time = time.time()
last_tick_time = time.time()


# --------------------------------------------------
# PLAYER REQUEST MODEL
# --------------------------------------------------

class PlayerJoin(BaseModel):
    player_id: str = "anonymous"


# --------------------------------------------------
# SIMULATED GAME CPU WORK
# --------------------------------------------------

def simulate_player_processing(player_number: int):
    """
    Simulates the CPU work required to process
    one player's game-state update.
    """

    result = 0.0

    for i in range(5000):
        result += math.sin(i + player_number) * math.cos(i)

    return result


# --------------------------------------------------
# GAME LOOP
# --------------------------------------------------

async def game_loop():
    """
    Simulates a real-time multiplayer game loop.

    The loop runs approximately 20 times per second,
    representing a 20 Hz game tick rate.
    """

    global tick_count
    global last_tick_time

    while True:

        tick_start = time.time()

        # Process every active player during this tick.
        for player in range(active_players):
            simulate_player_processing(player)

        tick_count += 1
        last_tick_time = time.time()

        # Maintain approximately 20 ticks per second.
        elapsed = time.time() - tick_start
        sleep_time = max(0, 0.05 - elapsed)

        await asyncio.sleep(sleep_time)


# --------------------------------------------------
# START GAME LOOP WHEN SERVER STARTS
# --------------------------------------------------

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(game_loop())


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
async def health_check():

    return {
        "status": "healthy",
        "server": "game-lobby"
    }


# --------------------------------------------------
# SERVER STATUS
# --------------------------------------------------

@app.get("/status")
async def server_status():

    uptime = time.time() - server_start_time

    return {
        "status": "running",
        "active_players": active_players,
        "total_join_requests": total_join_requests,
        "tick_count": tick_count,
        "uptime_seconds": round(uptime, 2),
        "tick_rate_hz": 20
    }


# --------------------------------------------------
# JOIN MATCH ENDPOINT
# --------------------------------------------------

@app.post("/join-match")
async def join_match(player: PlayerJoin):

    global active_players
    global total_join_requests

    active_players += 1
    total_join_requests += 1

    # Simulate the CPU work involved in
    # creating a player's game session.
    simulate_player_processing(active_players)

    return {
        "message": "Player joined the game session",
        "player_id": player.player_id,
        "active_players": active_players,
        "server": os.getenv("HOSTNAME", "local-game-server")
    }