# AURA System Architecture

## Overview
AURA Privacy Guardian is engineered as an autonomous local service with strict layer separation:

1. **Hardware & OS Sensor Layer (`aura/sensors/`)**
   - DirectShow webcam availability query.
   - CoreAudio active microphone stream probe.
   - psutil CPU, Memory, Disk, Network I/O, and Socket inspection.
   - Process and network intelligence categorization.

2. **Dynamic Baseline & Anomaly Engine (`aura/engine/baseline.py`, `model.py`)**
   - Online metric tracking using Welford's algorithm and EWMA.
   - Dual-model unsupervised machine learning (Isolation Forest + LOF).
   - Cold-start safeguards requiring n >= 10 samples before declaring anomalies.

3. **Multi-Signal Correlation & Risk Layer (`aura/engine/correlation.py`, `aura/engine/risk_hardened.py`)**
   - Sliding 60s temporal correlation across hardware, network, and compute signals.
   - Anti-double-counting dampener for composite threat signals.
   - Deterministic 0-100 bounded risk score with structured provenance.

4. **Storage Layer (`aura/storage/sqlite.py`)**
   - SQLite WAL database at `%LOCALAPPDATA%\AURA\data\aura.db`.
   - Versioned migrations for telemetry snapshots, security events, baseline profiles, and scan runs.

5. **Local API & WebSocket Transport (`aura/api/`)**
   - FastAPI server bound to `127.0.0.1`.
   - Ephemeral bootstrap token handshake and sliding rate limiter.
   - Real-time WebSocket broadcasting with per-client queue isolation.

6. **Web Dashboard (`web/`)**
   - React 19 + TypeScript SPA served locally.
