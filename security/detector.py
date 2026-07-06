import psutil

def get_process_data():
    processes = []
    cpu_count = psutil.cpu_count()

    for proc in psutil.process_iter():
        try:
            with proc.oneshot():
                processes.append({
                    "pid": proc.pid,
                    "name": proc.name(),
                    "cpu_percent": round(proc.cpu_percent() / cpu_count, 2),
                    "memory_percent": round(proc.memory_percent(), 2)
                })
        except:
            continue

    return processes