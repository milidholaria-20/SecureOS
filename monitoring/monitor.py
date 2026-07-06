import psutil
from datetime import datetime

def get_cpu():
    return psutil.cpu_percent(interval=1)

def get_memory():
    return psutil.virtual_memory().percent

def get_disk():
    disk = psutil.disk_usage('/')
    return round(disk.percent, 1)

def get_network():
    net = psutil.net_io_counters()
    return {
        "bytes_sent_mb": round(net.bytes_sent / (1024 * 1024), 2),
        "bytes_recv_mb": round(net.bytes_recv / (1024 * 1024), 2)
    }

def get_processes():
    processes = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
        try:
            processes.append(p.info)
        except Exception:
            continue
    return processes

def log_cpu_data(cpu, memory):
    try:
        with open("data/cpu_data.csv", "a") as f:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{ts},{cpu},{memory}\n")
    except Exception as e:
        print("Logging error:", e)
