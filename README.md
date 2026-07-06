# 🛡️ SecureOS — AI-Assisted OS Resource & Security Manager

SecureOS is a lightweight operating-systems management layer that sits on top of Linux
and combines **real-time system monitoring**, **ML-based anomaly detection**,
**predictive load forecasting**, **automated container management**, and a
**CPU scheduling simulator** — all in one interactive dashboard.

It was built as an Operating Systems course project to demonstrate how classical OS
concepts (process management, scheduling, resource monitoring) can be paired with
practical machine learning to build something closer to what real cloud platforms do.

> Built with Python, scikit-learn, psutil, Docker, and Streamlit.

---

## ✨ Features

| Module | What it does |
|---|---|
| **Live System Monitoring** | Streams CPU, memory, disk, and network usage in real time using `psutil`. |
| **ML Anomaly Detection** | An unsupervised **Isolation Forest** learns each machine's normal per-process CPU/memory behavior and flags outliers — no labeled attack data required. Falls back to threshold rules while the model is still warming up. |
| **Predictive Load Forecasting** | A **Linear Regression** model predicts near-future memory load from CPU trends, feeding the container manager so it can react *before* the system is overloaded. |
| **Automated Container Management** | Watches CPU load + predictions and automatically stops/starts Docker containers to keep the system stable. |
| **Process Manager** | Live, sortable process table with a **Kill Process** control (with a confirmation step to prevent accidental termination). |
| **CPU Scheduling Simulator** | Interactively compare **FCFS, SJF, Priority, and Round Robin** scheduling on the same workload — editable process table, Gantt charts per algorithm, and a side-by-side comparison of average waiting/turnaround time. |
| **Security Alert History** | Every anomaly is logged to JSON + plaintext, with severity breakdown charts and full history browsing. |

---

## 🏗️ Architecture

```
SecureOS/
├── main.py                     # Orchestrates one full monitoring + detection + AI + docker cycle
├── requirements.txt
├── monitoring/
│   └── monitor.py              # CPU, memory, disk, network, process snapshots
├── security/
│   ├── detector.py             # Per-process data collector
│   ├── analyser.py             # Isolation Forest anomaly detection + process history
│   └── logger.py               # Alert persistence (JSON + plaintext)
├── ai_engine/
│   └── predictor.py            # Linear Regression (load forecast) + system-level Isolation Forest
├── docker_manager/
│   └── docker_ops.py           # Container list/start/stop + auto-management policy
├── scheduling/
│   └── scheduler.py            # FCFS, SJF, Priority, Round Robin — pure functions, fully testable
├── dashboard/
│   └── app.py                  # Streamlit UI — 6 pages tying every module together
└── data/                       # Runtime-generated logs & history (git-ignored, regenerates on run)
```

Each module is independent and importable on its own — `scheduling/scheduler.py`, for
example, has no dependency on Streamlit or psutil, so the algorithms can be unit tested
or reused outside the dashboard entirely.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- (Optional) Docker, if you want to see the Container Manager page do something real

### Install

```bash
git clone https://github.com/<your-username>/SecureOS.git
cd SecureOS
pip install -r requirements.txt
```

### Run

```bash
python -m streamlit run dashboard/app.py
```

The dashboard opens automatically at `http://localhost:8501`.

> **Note:** the Isolation Forest models need ~20 samples before they switch from
> threshold-based rules to full ML detection, and the Linear Regression predictor
> needs 10+ samples — this happens automatically after a few refreshes/minutes of
> the dashboard running.

---

## 🧠 Why Isolation Forest?

Isolation Forest is unsupervised, so it doesn't need pre-labeled "malicious process"
data — something that's rarely available for a real, unique machine. Instead, it learns
the *shape* of normal CPU/memory behavior for this specific system and isolates points
that are unusually easy to separate from the rest — that's the anomaly signal. This
means a process using 60% CPU on a machine that's normally busy won't be flagged, but
the same usage on a machine that's normally idle will be.

Two Isolation Forests run in this project:
- `security/analyser.py` — scores **individual processes** for suspicious behavior.
- `ai_engine/predictor.py` — scores the **overall system state** (CPU + memory together).

## 🧮 CPU Scheduling Simulator

The `scheduling/scheduler.py` module implements four textbook algorithms sharing a
common interface, so they can be run and compared identically:

- **FCFS** — strict arrival order.
- **SJF (non-preemptive)** — shortest burst time among arrived processes runs next.
- **Priority (non-preemptive)** — lowest priority value runs next.
- **Round Robin** — preemptive, fixed time quantum, classic circular queue.

Each returns Gantt-chart segments plus per-process completion/turnaround/waiting time,
which the dashboard renders as an interactive comparison so you can see *why* one
algorithm beats another on a given workload — for example, why Round Robin trades
worse average waiting time for better response time under bursty arrivals.

---

## 🛠️ Tech Stack

- **Python** — core language
- **psutil** — system & process introspection
- **scikit-learn** — Isolation Forest, Linear Regression
- **pandas / numpy** — data wrangling
- **Streamlit** — dashboard UI
- **Plotly** — interactive charts (time series, gauges, Gantt charts)
- **Docker (subprocess)** — container lifecycle management

---

## 📌 Possible Next Steps

- Persist trained models to disk so they survive a dashboard restart.
- Swap the CSV/JSON data files for SQLite once history grows large.
- Add preemptive SJF (Shortest Remaining Time First) and Multilevel Feedback Queue.
- Containerize SecureOS itself with a `Dockerfile` for one-command deployment.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
