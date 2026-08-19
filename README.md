# AURA Privacy Guardian

AURA is an academic privacy-monitoring prototype that combines machine-learning anomaly detection with system and network activity indicators.

## Detection layers

1. CPU and outbound network-rate monitoring
2. Camera availability probe
3. Running-process count
4. Active remote-connection count
5. Inventory of sensitive-looking files in common user folders
6. Isolation Forest
7. Local Outlier Factor (LOF)
8. Rule-based privacy-risk scoring
9. Potential data-exfiltration pattern flagging

## Important technical scope

AURA is a **privacy anomaly and risk-indication system**, not a forensic data-loss-prevention product.

A potential data-exfiltration event means that AURA observed suspicious outbound activity combined with other indicators. It does not prove that a file was stolen or identify the exact leaked content.

The camera feature is an availability probe. It does not prove that another process is using the camera. Reliable camera-access attribution requires OS-specific privacy telemetry.

Sensitive-file monitoring only counts files with common sensitive extensions in common user folders. It does not read their contents.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Safe demonstration

Enable **Run simulated privacy-threat test** in the sidebar. This creates synthetic abnormal CPU/network values and runs them through the same detection/risk pipeline. It does not attack the computer or transmit any data.
