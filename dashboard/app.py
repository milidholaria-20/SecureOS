import streamlit as st
import pandas as pd
import json
import os
import sys
import psutil
import subprocess
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import run_system
from ai_engine.predictor import is_trained
from security.analyser import is_model_trained
from scheduling.scheduler import run_all as run_all_schedulers

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SecureOS Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .section-header {
        font-size: 1.1rem; font-weight: 700;
        color: #4f8bf9; margin: 20px 0 10px 0;
        border-bottom: 1px solid #2d3250; padding-bottom: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/shield.png", width=64)
    st.title("SecureOS")
    st.divider()

    auto_refresh = st.toggle("Auto Refresh (5s)", value=False)
    if auto_refresh:
        import time
        time.sleep(5)
        st.rerun()

    st.divider()
    page = st.radio("Navigate", [
        "📊 Dashboard",
        "🔐 Security Alerts",
        "📋 Process Manager",
        "🤖 AI & Prediction",
        "🐳 Container Manager",
        "🧮 CPU Scheduler",
    ])

# ── Run system ─────────────────────────────────────────────────────────────────
with st.spinner("Collecting system data..."):
    data = run_system()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    st.title("📊 System Dashboard")
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("⚡ CPU Usage",    f"{data['cpu']}%",
              delta=f"{'⚠ High' if data['cpu']>80 else 'Normal'}")
    c2.metric("🧠 Memory Usage", f"{data['memory']}%",
              delta=f"{'⚠ High' if data['memory']>80 else 'Normal'}")
    c3.metric("💾 Disk Usage",   f"{data['disk']}%")
    c4.metric("🔐 Active Alerts", len(data["alerts"]),
              delta=f"{'⚠ Check' if data['alerts'] else 'All Clear'}")

    n = data["network"]
    nc1, nc2 = st.columns(2)
    nc1.metric("📤 Network Sent", f"{n['bytes_sent_mb']} MB")
    nc2.metric("📥 Network Recv", f"{n['bytes_recv_mb']} MB")

    st.markdown('<p class="section-header">System Status</p>', unsafe_allow_html=True)
    if data["is_anomaly"]:
        st.error(f"🔴 ANOMALY DETECTED by AI — score: {data['anomaly_score']}")
    elif data["cpu"] > 80:
        st.error("🔴 High Load")
    elif data["cpu"] > 40:
        st.warning("🟡 Moderate Load")
    else:
        st.success("🟢 System Stable")

    st.markdown('<p class="section-header">CPU & Memory Over Time</p>', unsafe_allow_html=True)
    try:
        df = pd.read_csv("data/cpu_data.csv",
                         names=["time", "cpu", "memory"],
                         on_bad_lines='skip')
        df = df.dropna()
        df["cpu"]    = pd.to_numeric(df["cpu"],    errors="coerce")
        df["memory"] = pd.to_numeric(df["memory"], errors="coerce")
        df = df.dropna()
        df = df[(df["cpu"]>=0)&(df["cpu"]<=100)&(df["memory"]>=0)&(df["memory"]<=100)]
        df = df.tail(60)

        if len(df) > 1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=df["cpu"],    name="CPU %",
                                     line=dict(color="#4f8bf9", width=2),
                                     fill="tozeroy", fillcolor="rgba(79,139,249,0.1)"))
            fig.add_trace(go.Scatter(y=df["memory"], name="Memory %",
                                     line=dict(color="#ff7043", width=2),
                                     fill="tozeroy", fillcolor="rgba(255,112,67,0.1)"))
            fig.add_hline(y=80, line_dash="dash", line_color="red",
                          annotation_text="Danger Threshold")
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="white", height=300,
                margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h")
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Collecting data — refresh a few more times to see the chart.")
    except Exception as e:
        st.warning(f"Chart error: {e}")

    st.markdown('<p class="section-header">Disk Usage</p>', unsafe_allow_html=True)
    fig_disk = go.Figure(go.Indicator(
        mode="gauge+number",
        value=data["disk"],
        gauge=dict(
            axis=dict(range=[0, 100]),
            bar=dict(color="#4f8bf9"),
            steps=[
                dict(range=[0,  60], color="#1e2130"),
                dict(range=[60, 80], color="#2d3a1e"),
                dict(range=[80,100], color="#3a1e1e"),
            ],
            threshold=dict(line=dict(color="red", width=4), value=85)
        ),
        title=dict(text="Disk %", font=dict(color="white")),
        number=dict(font=dict(color="white"), suffix="%")
    ))
    fig_disk.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=220,
                           margin=dict(l=20,r=20,t=30,b=0))
    st.plotly_chart(fig_disk, width="stretch")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SECURITY ALERTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔐 Security Alerts":
    st.title("🔐 Security Alerts")

    ml_status = "✅ Active (Isolation Forest)" if is_model_trained() else "⏳ Warming up (threshold mode)"
    st.info(f"**ML Engine:** {ml_status}")

    st.markdown('<p class="section-header">Current Alerts</p>', unsafe_allow_html=True)
    if data["alerts"]:
        for a in data["alerts"]:
            sev = a.get("severity", "Low")
            color = "🔴" if sev=="High" else ("🟡" if sev=="Medium" else "🟢")
            ml_tag = "🤖 ML" if a.get("ml_active") else "📏 Rule"
            st.error(f"{color} **{a['name']}** (PID {a['pid']}) | {a['reason']} | {sev} | {ml_tag}")
    else:
        st.success("✅ No alerts — system clean")

    st.markdown('<p class="section-header">Alert History</p>', unsafe_allow_html=True)
    try:
        with open("data/alerts.json", "r") as f:
            history = json.load(f)
        if history:
            df_hist = pd.DataFrame(history)
            cols_show = [c for c in ["timestamp","name","pid","reason","severity","cpu_percent","memory_percent"] if c in df_hist.columns]
            st.dataframe(df_hist[cols_show].tail(50)[::-1], width="stretch")

            if "severity" in df_hist.columns:
                sev_counts = df_hist["severity"].value_counts().reset_index()
                sev_counts.columns = ["severity", "count"]
                fig_pie = px.pie(sev_counts, names="severity", values="count",
                                 color="severity",
                                 color_discrete_map={"High":"#ff4b4b","Medium":"#ffa500","Low":"#00cc88"},
                                 title="Alert Severity Distribution")
                fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                                      font_color="white", height=300)
                st.plotly_chart(fig_pie, width="stretch")
        else:
            st.info("No alert history yet.")
    except Exception:
        st.info("No alert history yet.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: PROCESS MANAGER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Process Manager":
    st.title("📋 Process Manager")
    st.caption("View running processes and kill suspicious ones.")

    procs = data["processes"]
    df_proc = pd.DataFrame(procs)

    if df_proc.empty:
        st.warning("No process data.")
    else:
        cols = [c for c in ["pid","name","cpu_percent","memory_percent","status"] if c in df_proc.columns]
        df_proc = df_proc[cols].fillna(0)
        df_proc = df_proc.sort_values("cpu_percent", ascending=False)
        st.dataframe(df_proc, width="stretch")

        # ── Kill process ────────────────────────────────────────────────────────
        st.markdown('<p class="section-header">Kill a Process</p>', unsafe_allow_html=True)
        kc1, kc2 = st.columns([3, 1])
        with kc1:
            pid_options = df_proc["pid"].tolist()
            label_map = {pid: f"{pid} — {name}" for pid, name in
                         zip(df_proc["pid"], df_proc.get("name", df_proc["pid"]))}
            target_pid = st.selectbox(
                "Select a process to terminate",
                options=pid_options,
                format_func=lambda p: label_map.get(p, str(p)),
            )
        with kc2:
            st.write("")  # vertical spacer to align the button with the selectbox
            st.write("")
            confirm = st.checkbox("Confirm", key="kill_confirm")
            if st.button("🛑 Kill Process", disabled=not confirm):
                try:
                    target = psutil.Process(int(target_pid))
                    target.terminate()
                    try:
                        target.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        target.kill()
                    st.success(f"Process {target_pid} terminated.")
                    st.session_state["kill_confirm"] = False
                    st.rerun()
                except psutil.NoSuchProcess:
                    st.warning("Process no longer exists.")
                except psutil.AccessDenied:
                    st.error("Access denied — try running the dashboard with elevated privileges.")
                except Exception as e:
                    st.error(f"Failed to terminate process: {e}")

    # ── Process history ────────────────────────────────────────────────────────
    st.markdown('<p class="section-header">Process History (per process)</p>', unsafe_allow_html=True)
    try:
        with open("data/process_history.json", "r") as f:
            ph = json.load(f)
        if ph:
            selected = st.selectbox("Select process to view history", options=list(ph.keys()))
            if selected:
                hist_df = pd.DataFrame(ph[selected])
                if not hist_df.empty:
                    fig_ph = go.Figure()
                    fig_ph.add_trace(go.Scatter(x=hist_df["time"], y=hist_df["cpu"],
                                                name="CPU %", line=dict(color="#4f8bf9")))
                    fig_ph.add_trace(go.Scatter(x=hist_df["time"], y=hist_df["memory"],
                                                name="Memory %", line=dict(color="#ff7043")))
                    fig_ph.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font_color="white", height=280,
                        title=f"Resource history: {selected}",
                        margin=dict(l=0,r=0,t=40,b=0)
                    )
                    st.plotly_chart(fig_ph, width="stretch")
        else:
            st.info("Process history builds up as the dashboard runs — refresh a few times.")
    except Exception:
        st.info("Process history builds up as the dashboard runs — refresh a few times.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: AI & PREDICTION
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🤖 AI & Prediction":
    st.title("🤖 AI Engine")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Load Prediction")
        st.caption("Linear Regression trained on CPU → Memory historical data.")
        if is_trained():
            pred = data["prediction"]
            st.metric("Predicted Memory Load", f"{pred}%" if pred else "N/A")
            st.success("✅ Model trained and active")
        else:
            st.warning("⏳ Collecting data to train model (need 10+ samples)...")

    with c2:
        st.markdown("### System Anomaly Detection")
        st.caption("Isolation Forest detects unusual CPU + Memory combinations.")
        if data["is_anomaly"]:
            st.error(f"🚨 ANOMALY DETECTED\nScore: {data['anomaly_score']}")
        else:
            st.success(f"✅ Normal\nAnomaly Score: {data['anomaly_score']}")

    # ── Scatter plot ───────────────────────────────────────────────────────────
    st.markdown("### CPU vs Memory — Historical Scatter")
    try:
        df = pd.read_csv("data/cpu_data.csv", names=["time","cpu","memory"], on_bad_lines='skip')
        df = df.dropna()
        df["cpu"]    = pd.to_numeric(df["cpu"],    errors="coerce")
        df["memory"] = pd.to_numeric(df["memory"], errors="coerce")
        df = df.dropna()
        df = df[(df["cpu"]>=0)&(df["cpu"]<=100)&(df["memory"]>=0)&(df["memory"]<=100)]
        if len(df) > 5:
            fig_sc = px.scatter(df, x="cpu", y="memory",
                                labels={"cpu":"CPU %","memory":"Memory %"},
                                color_discrete_sequence=["#4f8bf9"])
            fig_sc.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                                 plot_bgcolor="rgba(0,0,0,0)",
                                 font_color="white", height=320,
                                 margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig_sc, width="stretch")
        else:
            st.info("Chart available once more data is collected.")
    except Exception as e:
        st.info(f"Chart error: {e}")

    # ── Alert trend over time ─────────────────────────────────────────────────
    st.markdown("### Alert Frequency Over Time")
    try:
        with open("data/alerts.json","r") as f:
            alerts_hist = json.load(f)
        if alerts_hist:
            df_a = pd.DataFrame(alerts_hist)
            if "timestamp" in df_a.columns:
                df_a["timestamp"] = pd.to_datetime(df_a["timestamp"], errors="coerce")
                df_a = df_a.dropna(subset=["timestamp"])
                df_a["minute"] = df_a["timestamp"].dt.floor("min")
                trend = df_a.groupby("minute").size().reset_index(name="count")
                fig_t = go.Figure(go.Bar(x=trend["minute"], y=trend["count"],
                                         marker_color="#ff4b4b"))
                fig_t.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                                    plot_bgcolor="rgba(0,0,0,0)",
                                    font_color="white", height=250,
                                    margin=dict(l=0,r=0,t=10,b=0),
                                    xaxis_title="Time", yaxis_title="Alerts")
                st.plotly_chart(fig_t, width="stretch")
        else:
            st.info("Alert trend will appear once alerts are detected.")
    except Exception:
        st.info("Alert trend will appear once alerts are detected.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: CONTAINER MANAGER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🐳 Container Manager":
    st.title("🐳 Docker Container Manager")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🟢 Running Containers")
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.ID}} | {{.Names}} | {{.Status}} | {{.Image}}"],
                capture_output=True, text=True
            )
            running = result.stdout.strip()
            if running:
                for line in running.split("\n"):
                    parts = line.split("|")
                    if len(parts) >= 3:
                        cid, name, status = parts[0].strip(), parts[1].strip(), parts[2].strip()
                        st.success(f"**{name}** ({cid[:12]}) — {status}")
                        if st.button(f"Stop {name}", key=f"stop_{cid}"):
                            subprocess.run(["docker", "stop", cid])
                            st.warning(f"Stopping {name}...")
                            st.rerun()
            else:
                st.info("No running containers")
        except Exception as e:
            st.warning(f"Docker not available: {e}")

    with col2:
        st.markdown("### 🔵 Start a Container")
        image = st.selectbox("Choose image", ["nginx", "alpine", "redis", "hello-world"])
        if st.button("▶️ Start Container"):
            try:
                subprocess.run(["docker", "run", "-d", image], check=True)
                st.success(f"Started {image}")
                st.rerun()
            except Exception as e:
                st.error(f"Failed: {e}")

    st.markdown("### 📋 All Containers (including stopped)")
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Image}}"],
            capture_output=True, text=True
        )
        if result.stdout.strip():
            st.code(result.stdout)
        else:
            st.info("No containers found.")
    except Exception:
        st.info("Docker not available.")

    if data["docker_action"] != "none":
        st.info(f"🤖 Auto action taken: `{data['docker_action']}`")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: CPU SCHEDULER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🧮 CPU Scheduler":
    st.title("🧮 CPU Scheduling Simulator")
    st.caption("Classic OS scheduling algorithms — FCFS, SJF, Priority, and Round Robin — "
               "compared side by side on the same workload.")

    # ── Process input ───────────────────────────────────────────────────────────
    st.markdown('<p class="section-header">Process Table</p>', unsafe_allow_html=True)
    st.caption("Edit burst / arrival / priority below, or use the defaults, then run the simulation.")

    default_procs = pd.DataFrame([
        {"pid": "P1", "arrival": 0, "burst": 5, "priority": 2},
        {"pid": "P2", "arrival": 1, "burst": 3, "priority": 1},
        {"pid": "P3", "arrival": 2, "burst": 8, "priority": 3},
        {"pid": "P4", "arrival": 3, "burst": 6, "priority": 2},
    ])

    edited = st.data_editor(
        default_procs,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "pid": st.column_config.TextColumn("Process ID", required=True),
            "arrival": st.column_config.NumberColumn("Arrival Time", min_value=0, step=1, required=True),
            "burst": st.column_config.NumberColumn("Burst Time", min_value=1, step=1, required=True),
            "priority": st.column_config.NumberColumn(
                "Priority (lower = higher)", min_value=0, step=1, required=True
            ),
        },
    )

    quantum = st.slider("Round Robin Time Quantum", min_value=1, max_value=10, value=2)
    run_sim = st.button("▶️ Run Simulation", type="primary")

    def _to_process_list(df):
        procs = []
        for _, row in df.iterrows():
            if pd.isna(row.get("pid")) or str(row.get("pid")).strip() == "":
                continue
            procs.append({
                "pid": str(row["pid"]),
                "arrival": int(row["arrival"]) if not pd.isna(row["arrival"]) else 0,
                "burst": max(1, int(row["burst"]) if not pd.isna(row["burst"]) else 1),
                "priority": int(row["priority"]) if not pd.isna(row.get("priority")) else 0,
            })
        return procs

    if run_sim:
        procs = _to_process_list(edited)
        if len(procs) < 1:
            st.warning("Add at least one process to run the simulation.")
        else:
            try:
                results = run_all_schedulers(procs, quantum=quantum)
                st.session_state["sched_results"] = results
            except Exception as e:
                st.error(f"Simulation error: {e}")

    if "sched_results" in st.session_state:
        results = st.session_state["sched_results"]

        # ── Comparison table ─────────────────────────────────────────────────────
        st.markdown('<p class="section-header">Algorithm Comparison</p>', unsafe_allow_html=True)
        comparison = pd.DataFrame([
            {
                "Algorithm": name,
                "Avg Waiting Time": round(r["avg_waiting"], 2),
                "Avg Turnaround Time": round(r["avg_turnaround"], 2),
            }
            for name, r in results.items()
        ])
        best_wait = comparison["Avg Waiting Time"].idxmin()
        st.dataframe(
            comparison.style.highlight_min(subset=["Avg Waiting Time", "Avg Turnaround Time"],
                                            color="rgba(0,204,136,0.35)"),
            width="stretch",
        )
        st.success(
            f"🏆 **{comparison.loc[best_wait, 'Algorithm']}** gives the lowest average "
            f"waiting time ({comparison.loc[best_wait, 'Avg Waiting Time']}) for this workload."
        )

        fig_cmp = go.Figure()
        fig_cmp.add_trace(go.Bar(name="Avg Waiting Time",
                                  x=comparison["Algorithm"], y=comparison["Avg Waiting Time"],
                                  marker_color="#4f8bf9"))
        fig_cmp.add_trace(go.Bar(name="Avg Turnaround Time",
                                  x=comparison["Algorithm"], y=comparison["Avg Turnaround Time"],
                                  marker_color="#ff7043"))
        fig_cmp.update_layout(
            barmode="group", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="white", height=320, margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h")
        )
        st.plotly_chart(fig_cmp, width="stretch")

        # ── Gantt charts per algorithm ───────────────────────────────────────────
        st.markdown('<p class="section-header">Gantt Charts</p>', unsafe_allow_html=True)
        algo_tabs = st.tabs(list(results.keys()))
        palette = px.colors.qualitative.Set2

        for tab, (name, r) in zip(algo_tabs, results.items()):
            with tab:
                gantt_df = pd.DataFrame(r["gantt"])
                pids = sorted(gantt_df["pid"].unique())
                color_map = {pid: palette[i % len(palette)] for i, pid in enumerate(pids)}

                fig_g = go.Figure()
                for _, seg in gantt_df.iterrows():
                    fig_g.add_trace(go.Bar(
                        x=[seg["end"] - seg["start"]],
                        y=["CPU"],
                        base=[seg["start"]],
                        orientation="h",
                        name=seg["pid"],
                        marker_color=color_map[seg["pid"]],
                        text=seg["pid"],
                        textposition="inside",
                        showlegend=False,
                        hovertemplate=f"{seg['pid']}: {seg['start']}–{seg['end']}<extra></extra>",
                    ))
                fig_g.update_layout(
                    barmode="stack", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font_color="white", height=180, margin=dict(l=0, r=0, t=10, b=0),
                    xaxis_title="Time", showlegend=False,
                )
                st.plotly_chart(fig_g, width="stretch")

                table_df = pd.DataFrame(r["table"])
                st.dataframe(table_df, width="stretch")
                st.caption(
                    f"Avg Waiting Time: **{round(r['avg_waiting'], 2)}** | "
                    f"Avg Turnaround Time: **{round(r['avg_turnaround'], 2)}**"
                )
    else:
        st.info("Configure the process table above and click **Run Simulation**.")

