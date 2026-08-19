from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from aura_core import get_or_create_baseline, scan_once, train_aura_model
from logger import load_logs

st.set_page_config(
    page_title="AURA Privacy Guardian",
    page_icon="🛡️",
    layout="wide",
)

st.markdown(
    """
    <style>
    .main { background: #f5f7fa; }
    .aura-note {
        padding: 12px 16px;
        border-radius: 10px;
        border: 1px solid #d9dee7;
        background: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def load_model():
    baseline = get_or_create_baseline()
    return train_aura_model(baseline)


st.title("🛡️ AURA Privacy Guardian")
st.caption(
    "Privacy-focused anomaly monitoring using Isolation Forest, LOF, "
    "system activity indicators and network-behaviour heuristics."
)

with st.sidebar:
    st.header("Controls")

    probe_camera = st.checkbox(
        "Enable camera availability probe",
        value=False,
        help="Checks whether a camera can be opened. It does not prove another application is using it.",
    )

    if st.button("Retrain Detection Model", use_container_width=True):
        load_model.clear()
        st.rerun()

    st.divider()
    st.subheader("🧪 Demonstration Mode")
    demo_mode = st.checkbox(
        "Run simulated privacy-threat test",
        value=False,
        help="This is a safe synthetic test. It does not upload data or attack the system.",
    )

    st.info(
        "AURA provides anomaly and risk indicators. "
        "A 'potential data exfiltration' event means behaviour is suspicious; "
        "it is not proof that data was actually stolen."
    )

try:
    model = load_model()
except Exception as exc:
    st.error(f"Model initialization failed: {exc}")
    st.stop()

logs = load_logs()

latest_anomaly = int(logs["Anomaly"].iloc[-1]) if not logs.empty else 0
latest_risk = str(logs["Risk"].iloc[-1]) if not logs.empty else "NORMAL"
total_anomalies = int(logs["Anomaly"].sum()) if not logs.empty else 0
privacy_events = int(logs["Privacy_Event"].sum()) if not logs.empty and "Privacy_Event" in logs else 0
exfil_events = int(logs["Potential_Data_Exfiltration"].sum()) if not logs.empty and "Potential_Data_Exfiltration" in logs else 0

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("Current Protection", "ALERT" if latest_anomaly else "PROTECTED")

with c2:
    st.metric("Total Anomalies", total_anomalies)

with c3:
    st.metric("Privacy Events", privacy_events)

with c4:
    st.metric("Current Risk", latest_risk)

st.divider()

st.subheader("🔎 Live Privacy Scan")

if demo_mode:
    st.warning(
        "DEMO MODE: synthetic abnormal CPU/network activity is used only to "
        "demonstrate the detection pipeline."
    )

if st.button("Run AURA Scan", type="primary", use_container_width=True):
    synthetic = (
        {"CPU": 96.0, "Net": 5000.0, "Cam": 0}
        if demo_mode
        else None
    )

    with st.spinner("Collecting indicators and running anomaly detection..."):
        result = scan_once(model, probe_camera=probe_camera, synthetic=synthetic)

    if result["risk"] == "HIGH":
        st.error("🚨 HIGH RISK — multiple suspicious indicators detected.")
    elif result["risk"] == "MEDIUM":
        st.warning("⚠️ MEDIUM RISK — unusual activity requires attention.")
    else:
        st.success("✅ NORMAL — no significant anomaly detected.")

    if result["potential_data_exfiltration"]:
        st.error(
            "📤 POTENTIAL DATA-EXFILTRATION PATTERN: unusually high outbound "
            "activity combined with other suspicious indicators."
        )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("CPU", f"{result['CPU']:.1f}%")
    m2.metric("Outbound Rate", f"{result['Net']:.2f} KB/s")
    m3.metric("Processes", result["Process_Count"])
    m4.metric("Remote Connections", result["Remote_Connections"])

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Camera", result["camera_status"])
    m6.metric("Sensitive Files", result["Sensitive_Files"])
    m7.metric("IF", "ANOMALY" if result["if_anomaly"] else "NORMAL")
    m8.metric("LOF", "ANOMALY" if result["lof_anomaly"] else "NORMAL")

    st.write("**Why AURA flagged this event:**")
    for reason in result["reasons"]:
        st.write(f"• {reason}")

    st.caption(
        f"Risk score: {result['risk_score']} | "
        f"IF score: {result['if_score']} | LOF score: {result['lof_score']}"
    )

st.divider()

st.subheader("🕵️ Privacy Indicators")

p1, p2, p3 = st.columns(3)

if logs.empty:
    current_processes = 0
    current_remote = 0
    current_sensitive = 0
else:
    current_processes = int(logs["Process_Count"].iloc[-1])
    current_remote = int(logs["Remote_Connections"].iloc[-1])
    current_sensitive = int(logs["Sensitive_Files"].iloc[-1])

with p1:
    st.metric("Running Processes", current_processes)

with p2:
    st.metric("Remote Connections", current_remote)

with p3:
    st.metric("Sensitive-looking Files", current_sensitive)

st.caption(
    "Sensitive-file count is an inventory indicator based on common user folders "
    "and file extensions. AURA does not read file contents and does not claim a file was leaked."
)

st.divider()

st.subheader("📈 Activity Monitoring")

logs = load_logs()

if logs.empty:
    st.info("No monitoring events recorded yet. Click 'Run AURA Scan' above.")
else:
    chart_col1, chart_col2 = st.columns(2)

    chart_data = logs.tail(50).copy()

    with chart_col1:
        st.markdown("**CPU Usage (%)**")
        st.line_chart(chart_data.set_index("Timestamp")["CPU"])

    with chart_col2:
        st.markdown("**Outbound Network Rate (KB/s)**")
        st.line_chart(chart_data.set_index("Timestamp")["Net"])

    st.markdown("**Process Count**")
    st.line_chart(chart_data.set_index("Timestamp")["Process_Count"])

    st.markdown("**Remote Connection Count**")
    st.line_chart(chart_data.set_index("Timestamp")["Remote_Connections"])

    st.subheader("🚨 Recent Security Events")

    display_cols = [
        "Timestamp", "CPU", "Net", "Cam", "Process_Count",
        "Remote_Connections", "IF_Anomaly", "LOF_Anomaly",
        "Anomaly", "Risk", "Risk_Score", "Network_Level",
        "Privacy_Event", "Potential_Data_Exfiltration",
    ]
    available = [c for c in display_cols if c in logs.columns]

    st.dataframe(
        logs[available].tail(20).iloc[::-1],
        use_container_width=True,
        hide_index=True,
    )

st.divider()

st.subheader("ℹ️ What AURA Can and Cannot Claim")

st.markdown(
    """
    **AURA can identify:**
    - unusual CPU/network behaviour;
    - statistical anomalies using Isolation Forest and LOF;
    - unusually high outbound activity;
    - process-count and remote-connection deviations;
    - potential data-exfiltration patterns based on combined indicators.

    **AURA does not currently prove:**
    - that a specific file was stolen;
    - which exact application leaked data;
    - that a camera is being secretly accessed by another application;
    - that malware or spyware is present.

    These limitations are intentional so that the system's results remain technically defensible.
    """
)

st.caption("AURA Privacy Guardian • Academic Project Prototype")
