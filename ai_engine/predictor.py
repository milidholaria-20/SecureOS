import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
import os

# Linear regression for load prediction
_lr_model = LinearRegression()
_lr_trained = False

# Isolation forest for system-level anomaly
_sys_iso = IsolationForest(contamination=0.1, random_state=42)
_sys_iso_trained = False

def train_model():
    global _lr_model, _lr_trained, _sys_iso, _sys_iso_trained

    try:
        if not os.path.exists("data/cpu_data.csv"):
            return

        data = pd.read_csv("data/cpu_data.csv", names=["time", "cpu", "memory"],
                           on_bad_lines='skip')
        data = data.dropna()
        data = data[pd.to_numeric(data["cpu"], errors='coerce').notna()]
        data["cpu"] = pd.to_numeric(data["cpu"])
        data["memory"] = pd.to_numeric(data["memory"])
        data = data[(data["cpu"] >= 0) & (data["cpu"] <= 100) &
                    (data["memory"] >= 0) & (data["memory"] <= 100)]

        if len(data) < 10:
            print("Not enough clean data to train")
            return

        X = data[["cpu"]]
        y = data["memory"]
        _lr_model.fit(X, y)
        _lr_trained = True

        # Also train system-level isolation forest
        X_sys = data[["cpu", "memory"]].values
        _sys_iso.fit(X_sys)
        _sys_iso_trained = True

        print(f"Models trained on {len(data)} samples")

    except Exception as e:
        print("Training error:", e)
        _lr_trained = False

def predict(cpu):
    if not _lr_trained:
        return None
    try:
        inp = pd.DataFrame([[cpu]], columns=["cpu"])
        return round(float(_lr_model.predict(inp)[0]), 2)
    except Exception:
        return None

def system_anomaly_score(cpu, memory):
    """Returns (is_anomaly: bool, score: float) for the overall system state."""
    if not _sys_iso_trained:
        return False, 0.0
    try:
        score = float(_sys_iso.decision_function([[cpu, memory]])[0])
        label = int(_sys_iso.predict([[cpu, memory]])[0])
        return label == -1, round(score, 4)
    except Exception:
        return False, 0.0

def is_trained():
    return _lr_trained
