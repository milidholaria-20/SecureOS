from datetime import datetime
import json
import os

ALERTS_JSON = "data/alerts.json"
LOGS_TXT    = "data/logs.txt"

def log_alerts(alerts):
    with open(LOGS_TXT, "a") as f:
        for alert in alerts:
            f.write(f"{datetime.now()} | {alert}\n")

def save_alerts_to_json(alerts):
    # Append to history, not overwrite
    existing = []
    if os.path.exists(ALERTS_JSON):
        try:
            with open(ALERTS_JSON, "r") as f:
                existing = json.load(f)
                if not isinstance(existing, list):
                    existing = []
        except Exception:
            existing = []

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for a in alerts:
        a["timestamp"] = ts

    existing.extend(alerts)
    # Keep last 500 alerts
    existing = existing[-500:]

    with open(ALERTS_JSON, "w") as f:
        json.dump(existing, f, indent=2)
