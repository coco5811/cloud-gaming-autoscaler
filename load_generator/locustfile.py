"""Player load injector for the cloud-gaming autoscaler.

Run (headless, saves CSVs for the plotter):
  locust -f locustfile.py --headless -u 300 -r 20 -t 3m \
         --host http://localhost:30090 --csv results/managed
Or omit --headless and open http://localhost:8089 for the live UI.
"""
import random
import uuid

from locust import HttpUser, task, between, events


class GameClient(HttpUser):
    # Each simulated player fires requests every 0.1-0.5 s (aggressive on purpose)
    wait_time = between(0.1, 0.5)

    def on_start(self):
        self.player_id = f"player-{uuid.uuid4().hex[:8]}"

    @task(10)
    def join_match(self):
        payload = {
            "player_id": self.player_id,
            "region": random.choice(["ap-south", "eu-west", "us-east"]),
            "x": random.uniform(0, 1000),
            "y": random.uniform(0, 1000),
        }
        
        with self.client.post("/join-match", json=payload,
                      catch_response=True, name="/join-match") as r:
                        if r.status_code != 200:
                          r.failure(f"HTTP {r.status_code}")


    @task(1)
    def check_status(self):
        self.client.get("/status", name="/status")


@events.test_start.add_listener
def _start(environment, **kw):
    print(f"[locust] Flooding {environment.host}")
