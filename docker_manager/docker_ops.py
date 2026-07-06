import subprocess

def list_containers():
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.ID}} {{.Names}} {{.Status}}"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except Exception:
        return ""

def list_all_containers():
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.ID}} {{.Names}} {{.Status}}"],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    except Exception:
        return ""

def _container_exists(name):
    """Check if a container with this name already exists (running or stopped)."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name=^/{name}$", "--format", "{{.Names}}"],
            capture_output=True, text=True
        )
        return name in result.stdout
    except Exception:
        return False

def run_container(image="nginx"):
    container_name = f"secureos_{image}"
    try:
        if _container_exists(container_name):
            # Container exists but is stopped — just restart it
            subprocess.run(["docker", "start", container_name], check=True)
        else:
            # Fresh container
            subprocess.run(["docker", "run", "-d", "--name", container_name, image], check=True)
        return True
    except Exception as e:
        print("Run container error:", e)
        return False

def stop_container(container_id):
    try:
        subprocess.run(["docker", "stop", container_id], check=True)
        with open("data/last_stopped.txt", "w") as f:
            f.write(container_id)
        return True
    except Exception as e:
        print("Stop container error:", e)
        return False

def stop_first_container():
    output = list_containers()
    if not output:
        return None
    container_id = output.split("\n")[0].split()[0]
    stop_container(container_id)
    return container_id

def auto_manage_containers(cpu, prediction):
    action = "none"
    if cpu > 80 or (prediction is not None and prediction > 80):
        cid = stop_first_container()
        if cid:
            action = f"stopped:{cid}"
    elif cpu < 30:
        running = list_containers()
        if not running:
            run_container()
            action = "started:nginx"
    return action
