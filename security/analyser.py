import numpy as np
from sklearn.ensemble import IsolationForest
from datetime import datetime
import json
import os

# ─── Isolation Forest Model ───────────────────────────────────────────────────
_iso_model = IsolationForest(contamination=0.15, random_state=42)
_model_trained = False
_history = []          # rolling window of (cpu, memory) for training

HISTORY_MIN = 20       # need at least this many samples before training
HISTORY_MAX = 200      # cap to avoid unbounded growth

PROCESS_HISTORY_FILE = "data/process_history.json"

# ─── Process history (per-process tracking) ───────────────────────────────────
def _load_process_history():
    if os.path.exists(PROCESS_HISTORY_FILE):
        try:
            with open(PROCESS_HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_process_history(hist):
    try:
        with open(PROCESS_HISTORY_FILE, "w") as f:
            json.dump(hist, f, indent=2)
    except Exception as e:
        print("Warning: Could not save process history:", e)

def update_process_history(processes):
    """Append current snapshot to per-process history file."""
    hist = _load_process_history()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for p in processes:
        name = p["name"]
        if name not in hist:
            hist[name] = []
        hist[name].append({
            "time": ts,
            "cpu": p["cpu_percent"],
            "memory": p["memory_percent"]
        })
        hist[name] = hist[name][-50:]
    _save_process_history(hist)

def get_severity(cpu, memory):
    if cpu > 80 or memory > 80:
        return "High"
    elif cpu > 40 or memory > 40:
        return "Medium"
    return "Low"

def detect_suspicious(processes):
    global _iso_model, _model_trained, _history
    suspicious = []
    IGNORE = {"System Idle Process", "System", "idle"}

    for proc in processes:
        if proc["name"] in IGNORE:
            continue
        _history.append([proc["cpu_percent"], proc["memory_percent"]])

    if len(_history) > HISTORY_MAX:
        _history = _history[-HISTORY_MAX:]

    if len(_history) >= HISTORY_MIN:
        try:
            X = np.array(_history)
            _iso_model.fit(X)
            _model_trained = True
        except Exception as e:
            print("Isolation Forest training error:", e)
            _model_trained = False

    for proc in processes:
        name = proc["name"]
        if name in IGNORE:
            continue
        cpu = proc["cpu_percent"]
        mem = proc["memory_percent"]
        reasons = []

        if _model_trained:
            score = _iso_model.decision_function([[cpu, mem]])[0]
            label = _iso_model.predict([[cpu, mem]])[0]
            if label == -1:
                reasons.append(f"ML Anomaly (score={score:.2f})")
        else:
            if cpu > 50:
                reasons.append("High CPU (threshold)")
            if mem > 50:
                reasons.append("High Memory (threshold)")

        if reasons:
            suspicious.append({
                "pid": proc["pid"],
                "name": name,
                "cpu_percent": cpu,
                "memory_percent": mem,
                "reason": ", ".join(reasons),
                "severity": get_severity(cpu, mem),
                "ml_active": _model_trained
            })

    return suspicious

def is_model_trained():
    return _model_trained
