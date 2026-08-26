# AURA Privacy Guardian

[![AURA CI](https://github.com/Mandeepsai16/AURA-Privacy-Guardian/actions/workflows/ci.yml/badge.svg)](https://github.com/Mandeepsai16/AURA-Privacy-Guardian/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Windows 10/11](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg)](https://microsoft.com)

**AURA Privacy Guardian** is a lightweight, non-intrusive local cybersecurity and privacy protection platform for Windows 10 and 11. It continuously evaluates host behavioral envelopes, detects anomalous hardware and network interactions, and delivers transparent, explainable risk intelligence without capturing private user content or sending telemetry off-device.

---

## Key Capabilities

- **Autonomous Background Agent:** Runs as a dedicated Windows user daemon with Win32 Named Mutex single-instance protection and sleep/resume power handling.
- **Privacy Sentinel Probes:** DirectShow camera and CoreAudio microphone availability monitoring without capturing audio waveforms or video frames.
- **Dynamic Behavioral Baselines:** Online metric modeling using Welford's algorithm and EWMA with cold-start guards and outlier damping.
- **Unsupervised Anomaly Detection:** Dual-model Isolation Forest and Local Outlier Factor (LOF) multi-dimensional density estimation.
- **Multi-Signal Threat Correlation:** Contemporaneous correlation of hardware triggers, outbound WAN spikes, and process table velocities.
- **Hardened Explainable Risk Engine:** Deterministic 0–100 bounded scoring with structured contributor provenance and anti-double-counting.
- **High-Performance Local API:** Loopback-bound (`127.0.0.1`) REST API and WebSocket real-time event streaming with ephemeral single-use token authentication.
- **Modern Web Dashboard:** React 19 + TypeScript + Vite user interface with dark/light themes, live monitoring, privacy audits, and activity telemetry.

---

## Architectural Pipeline

```
[ Windows OS & Hardware ] ──> [ Sensor Collector ] ──> [ Dynamic Baselines ]
                                                               │
                                                               ▼
[ React Web Dashboard ] <── [ Loopback REST / WS ] <── [ Correlation & Hardened Risk ]
```

---

## Installation & Usage

### 1. Developer Setup
```powershell
# Clone repository
git clone https://github.com/Mandeepsai16/AURA-Privacy-Guardian.git
cd AURA-Privacy-Guardian

# Setup Python Virtual Environment
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run Test Suite
python -m pytest

# Build Frontend Assets
cd web
npm install
npm run build
cd ..

# Start AURA Agent
python -m aura.entrypoints.agent_main
```

### 2. Standalone Production Build
```powershell
python packaging/build.py
```

---

## Documentation

- [Architecture Guide](docs/ARCHITECTURE.md)
- [Installation & Deployment](docs/INSTALLATION.md)
- [Privacy Model & Data Policy](docs/PRIVACY.md)
- [Troubleshooting & Diagnostics](docs/TROUBLESHOOTING.md)
- [Release Baseline & Specification](docs/RELEASE_BASELINE.md)
- [Release Notes](docs/RELEASE.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)

---

## Privacy & Security Principles

AURA operates with strict data minimization:
1. **Zero Content Sniffing:** Packet payloads, clipboard text, and keystrokes are never recorded.
2. **Zero Audio/Video Capture:** Webcam frames and microphone recordings never touch disk or memory buffers.
3. **Local Loopback Only:** All APIs bind exclusively to `127.0.0.1`. No data leaves your machine.
