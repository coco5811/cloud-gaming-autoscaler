"""Telemetry for the slide deck.

1) While Locust runs, record cluster behaviour (separate terminal):
     python telemetry_plotter.py collect --out results/managed_cluster.csv --duration 200
2) After the test, plot one or more runs against each other:
     python telemetry_plotter.py plot \
        --run "Unmanaged (1 pod)"  results/unmanaged  results/unmanaged_cluster.csv \
        --run "HPA enabled"        results/managed    results/managed_cluster.csv

Each run = label, locust csv prefix (the --csv value), cluster csv from `collect`.
Experiment tip: for the 'unmanaged' run, `kubectl delete hpa <name>` and
`kubectl scale deploy game-server --replicas=1`, then re-apply the HPA afterwards.
"""
import argparse, csv, json, subprocess, time


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def collect(a):
    t0 = time.time()
    with open(a.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["epoch", "running_pods", "ready_pods", "cpu_pct"])
        while time.time() - t0 < a.duration:
            try:
                pods = json.loads(sh(["kubectl", "get", "pods", "-l", f"app={a.app}", "-o", "json"]))["items"]
                running = sum(p["status"].get("phase") == "Running" for p in pods)
                ready = sum(any(c["type"] == "Ready" and c["status"] == "True"
                                for c in p["status"].get("conditions", [])) for p in pods)
                cpu = ""
                hpa = json.loads(sh(["kubectl", "get", "hpa", "-o", "json"]))["items"]
                if hpa:
                    for m in hpa[0]["status"].get("currentMetrics", []):
                        if m["type"] == "Resource":
                            cpu = m["resource"]["current"].get("averageUtilization", "")
                w.writerow([round(time.time(), 1), running, ready, cpu]); f.flush()
                print(f"pods running={running} ready={ready} cpu={cpu}%")
            except Exception as e:
                print("collect error:", e)
            time.sleep(a.interval)


def plot(a):
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(2, 2, figsize=(14, 9))
    for label, prefix, cluster in a.run:
        h = pd.read_csv(f"{prefix}_stats_history.csv")
        h = h[h["Name"] == "Aggregated"]
        t = h["Timestamp"] - h["Timestamp"].min()
        ax[0][0].plot(t, h["Requests/s"], label=label)
        ax[0][1].plot(t, h["Failures/s"], label=label)
        ax[1][0].plot(t, h["95%"], label=label)
        c = pd.read_csv(cluster)
        ax[1][1].step(c["epoch"] - c["epoch"].min(), c["ready_pods"], where="post", label=label)

    titles = [("Throughput (requests/s)", "req/s"), ("Request failures/s", "fail/s"),
              ("95th percentile latency", "ms"), ("Ready game-server pods", "pods")]
    for axis, (title, yl) in zip(ax.flat, titles):
        axis.set_title(title); axis.set_xlabel("seconds since test start")
        axis.set_ylabel(yl); axis.grid(alpha=.3); axis.legend()
    plt.tight_layout()
    plt.savefig(a.out, dpi=150)
    print("saved", a.out)


p = argparse.ArgumentParser()
s = p.add_subparsers(dest="cmd", required=True)
c = s.add_parser("collect")
c.add_argument("--out", default="results/cluster.csv")
c.add_argument("--app", default="game-server")
c.add_argument("--duration", type=int, default=200)
c.add_argument("--interval", type=float, default=2)
c.set_defaults(fn=collect)
g = s.add_parser("plot")
g.add_argument("--run", nargs=3, action="append", metavar=("LABEL", "LOCUST_PREFIX", "CLUSTER_CSV"), required=True)
g.add_argument("--out", default="results/comparison.png")
g.set_defaults(fn=plot)
a = p.parse_args()
a.fn(a)
