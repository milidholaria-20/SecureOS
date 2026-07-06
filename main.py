from monitoring.monitor import get_cpu, get_memory, get_disk, get_network, get_processes, log_cpu_data
from security.detector import get_process_data
from security.analyser import detect_suspicious, update_process_history
from security.logger import log_alerts, save_alerts_to_json
from ai_engine.predictor import train_model, predict, system_anomaly_score
from docker_manager.docker_ops import auto_manage_containers

def run_system():
    # ── Monitoring ─────────────────────────────────────────────────────────────
    cpu     = get_cpu()
    memory  = get_memory()
    disk    = get_disk()
    network = get_network()
    processes = get_processes()

    log_cpu_data(cpu, memory)

    # ── Process history tracking ───────────────────────────────────────────────
    sec_data = get_process_data()
    update_process_history(sec_data)

    # ── ML-based Security Detection ────────────────────────────────────────────
    alerts = detect_suspicious(sec_data)

    # System-level high-load alert
    if cpu > 80:
        alerts.append({
            "pid": 0,
            "name": "System",
            "cpu_percent": cpu,
            "memory_percent": memory,
            "reason": "High overall CPU load",
            "severity": "High",
            "ml_active": False
        })

    if alerts:
        log_alerts(alerts)
        save_alerts_to_json(alerts)

    # ── AI Prediction & System Anomaly ─────────────────────────────────────────
    train_model()
    prediction   = predict(cpu)
    is_anomaly, anomaly_score = system_anomaly_score(cpu, memory)

    # ── Docker Management ──────────────────────────────────────────────────────
    docker_action = auto_manage_containers(cpu, prediction)

    return {
        "cpu":          cpu,
        "memory":       memory,
        "disk":         disk,
        "network":      network,
        "alerts":       alerts,
        "prediction":   prediction,
        "is_anomaly":   is_anomaly,
        "anomaly_score": anomaly_score,
        "processes":    processes[:15],
        "docker_action": docker_action
    }
