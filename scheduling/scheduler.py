"""
CPU Scheduling Simulator
------------------------
Implements four classic OS scheduling algorithms:

    * FCFS      - First Come First Served
    * SJF       - Shortest Job First (non-preemptive)
    * Priority  - Priority scheduling (non-preemptive, lower number = higher priority)
    * Round Robin - Time-quantum based preemptive scheduling

Every algorithm takes the same input (a list of process dicts) and returns
the same shape of output so the dashboard can render a Gantt chart and a
side-by-side comparison table regardless of which algorithm was chosen.

Input process dict:
    {"pid": str, "arrival": int, "burst": int, "priority": int (optional)}

Output dict:
    {
        "gantt": [{"pid": str, "start": int, "end": int}, ...],
        "table": [
            {"pid": str, "arrival": int, "burst": int, "completion": int,
             "turnaround": int, "waiting": int}, ...
        ],
        "avg_waiting": float,
        "avg_turnaround": float,
    }
"""

from copy import deepcopy


def _finalize(processes, completion_times):
    """Build the per-process metrics table + averages from completion times."""
    table = []
    total_wait = 0
    total_turnaround = 0

    for p in processes:
        pid = p["pid"]
        completion = completion_times[pid]
        turnaround = completion - p["arrival"]
        waiting = turnaround - p["burst"]
        total_wait += waiting
        total_turnaround += turnaround
        table.append({
            "pid": pid,
            "arrival": p["arrival"],
            "burst": p["burst"],
            "completion": completion,
            "turnaround": turnaround,
            "waiting": waiting,
        })

    n = len(processes)
    return table, (total_wait / n if n else 0), (total_turnaround / n if n else 0)


def fcfs(processes):
    """First Come First Served — run processes strictly in arrival order."""
    procs = sorted(deepcopy(processes), key=lambda p: (p["arrival"], p["pid"]))
    gantt = []
    completion_times = {}
    clock = 0

    for p in procs:
        start = max(clock, p["arrival"])
        end = start + p["burst"]
        gantt.append({"pid": p["pid"], "start": start, "end": end})
        completion_times[p["pid"]] = end
        clock = end

    table, avg_wait, avg_tat = _finalize(procs, completion_times)
    return {"gantt": gantt, "table": table, "avg_waiting": avg_wait, "avg_turnaround": avg_tat}


def sjf(processes):
    """Shortest Job First, non-preemptive: among arrived processes, run the shortest burst."""
    procs = deepcopy(processes)
    remaining = {p["pid"]: p for p in procs}
    gantt = []
    completion_times = {}
    clock = 0

    while remaining:
        available = [p for p in remaining.values() if p["arrival"] <= clock]
        if not available:
            # Jump forward in time to the next arrival
            clock = min(p["arrival"] for p in remaining.values())
            continue
        nxt = min(available, key=lambda p: (p["burst"], p["arrival"], p["pid"]))
        start = clock
        end = start + nxt["burst"]
        gantt.append({"pid": nxt["pid"], "start": start, "end": end})
        completion_times[nxt["pid"]] = end
        clock = end
        del remaining[nxt["pid"]]

    table, avg_wait, avg_tat = _finalize(procs, completion_times)
    return {"gantt": gantt, "table": table, "avg_waiting": avg_wait, "avg_turnaround": avg_tat}


def priority_scheduling(processes):
    """Priority scheduling, non-preemptive. Lower `priority` value = higher priority."""
    procs = deepcopy(processes)
    for p in procs:
        p.setdefault("priority", 0)
    remaining = {p["pid"]: p for p in procs}
    gantt = []
    completion_times = {}
    clock = 0

    while remaining:
        available = [p for p in remaining.values() if p["arrival"] <= clock]
        if not available:
            clock = min(p["arrival"] for p in remaining.values())
            continue
        nxt = min(available, key=lambda p: (p["priority"], p["arrival"], p["pid"]))
        start = clock
        end = start + nxt["burst"]
        gantt.append({"pid": nxt["pid"], "start": start, "end": end})
        completion_times[nxt["pid"]] = end
        clock = end
        del remaining[nxt["pid"]]

    table, avg_wait, avg_tat = _finalize(procs, completion_times)
    return {"gantt": gantt, "table": table, "avg_waiting": avg_wait, "avg_turnaround": avg_tat}


def round_robin(processes, quantum=2):
    """Preemptive Round Robin with a fixed time quantum."""
    procs = sorted(deepcopy(processes), key=lambda p: (p["arrival"], p["pid"]))
    remaining_burst = {p["pid"]: p["burst"] for p in procs}
    arrival = {p["pid"]: p["arrival"] for p in procs}
    gantt = []
    completion_times = {}
    clock = 0
    queue = []
    not_yet_arrived = list(procs)
    visited = set()

    def enqueue_arrivals(now):
        nonlocal not_yet_arrived
        still = []
        for p in not_yet_arrived:
            if p["arrival"] <= now:
                queue.append(p["pid"])
                visited.add(p["pid"])
            else:
                still.append(p)
        not_yet_arrived = still

    enqueue_arrivals(clock)
    if not queue and not_yet_arrived:
        clock = min(p["arrival"] for p in not_yet_arrived)
        enqueue_arrivals(clock)

    while queue or not_yet_arrived:
        if not queue:
            clock = min(p["arrival"] for p in not_yet_arrived)
            enqueue_arrivals(clock)
            continue

        pid = queue.pop(0)
        run_time = min(quantum, remaining_burst[pid])
        start = clock
        end = start + run_time
        gantt.append({"pid": pid, "start": start, "end": end})
        remaining_burst[pid] -= run_time
        clock = end

        # New arrivals during this slice join the queue before the current
        # process is re-queued (standard convention), unless it just finished.
        enqueue_arrivals(clock)

        if remaining_burst[pid] > 0:
            queue.append(pid)
        else:
            completion_times[pid] = clock

    table, avg_wait, avg_tat = _finalize(procs, completion_times)
    return {"gantt": gantt, "table": table, "avg_waiting": avg_wait, "avg_turnaround": avg_tat}


ALGORITHMS = {
    "FCFS": fcfs,
    "SJF": sjf,
    "Priority": priority_scheduling,
    "Round Robin": round_robin,
}


def run_all(processes, quantum=2):
    """Run every algorithm on the same process set for side-by-side comparison."""
    results = {}
    for name, fn in ALGORITHMS.items():
        if name == "Round Robin":
            results[name] = fn(processes, quantum=quantum)
        else:
            results[name] = fn(processes)
    return results
