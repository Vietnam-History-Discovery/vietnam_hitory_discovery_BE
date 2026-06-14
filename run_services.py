#!/usr/bin/env python3
"""
Chạy tất cả Python microservices không cần Docker.

Usage:
    python run_services.py
    python run_services.py --svc graphrag
"""

import subprocess, sys, os, argparse, signal, time

ROOT = os.path.dirname(os.path.abspath(__file__))

SERVICES = {
    "graphrag":   {"port": 8001, "dir": os.path.join("services", "graphrag-service"),   "app": "app.main:app"},
    "ingestion":  {"port": 8002, "dir": os.path.join("services", "ingestion-service"),  "app": "app.main:app"},
    "evaluation": {"port": 8003, "dir": os.path.join("services", "evaluation-service"), "app": "app.main:app"},
}

processes = []

def start_service(name, config):
    cwd = os.path.join(ROOT, config["dir"])
    print(f"   dir: {cwd}")
    cmd = [
        sys.executable, "-m", "uvicorn",
        config["app"],
        "--host", "0.0.0.0",
        "--port", str(config["port"]),
        "--reload",
    ]
    print(f"🚀 Starting {name} on port {config['port']}...")
    proc = subprocess.Popen(cmd, cwd=cwd)
    processes.append(proc)
    return proc

def shutdown(sig, frame):
    print("\n⛔ Shutting down all services...")
    for p in processes:
        p.terminate()
    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--svc", choices=list(SERVICES.keys()))
    args = parser.parse_args()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    to_run = {args.svc: SERVICES[args.svc]} if args.svc else SERVICES

    for name, config in to_run.items():
        start_service(name, config)
        time.sleep(1)

    print(f"\n✅ {len(to_run)} service(s) running:")
    for name, config in to_run.items():
        print(f"   {name:12s} → http://localhost:{config['port']}")
        print(f"   {'docs':12s} → http://localhost:{config['port']}/docs")
    print("\nCtrl+C để dừng\n")

    try:
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        shutdown(None, None)