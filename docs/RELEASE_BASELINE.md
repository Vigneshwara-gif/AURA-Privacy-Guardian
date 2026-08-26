# AURA Privacy Guardian — Release Baseline Document

**Release Version:** `2.0.0`  
**Build Target:** Microsoft Windows 10 / Windows 11 (x64)  
**Classification:** Autonomous Local Endpoint Cybersecurity & Privacy Protection Platform  
**Schema Version:** `2`  

---

## 1. System Architecture Pipeline

The AURA production runtime is structured across 11 discrete, fault-isolated subsystems:

```
[ Windows OS / Hardware Sentinels ]
  ├── DirectShow Camera Probe (non-capturing state query)
  ├── Windows CoreAudio Device Enumerator (active stream count)
  ├── psutil Subsystem (CPU, RAM, Disk, Sockets, Process Table)
  └── Monotonic Clock Monitor (Sleep / Resume gap detector)
          │
          ▼
[ Sensor Collector (`aura/sensors/`) ]
  ├── Fault isolation per sensor (isolated try/except with health degradation)
  ├── Non-blocking sample acquisition
  └── Process & Network Intelligence (IP classifier, PID resolution)
          │
          ▼
[ Dynamic Behavioral Baseline (`aura/engine/baseline.py`) ]
  ├── Welford's Algorithm + EWMA (O(1) memory per metric)
  ├── Outlier damping (> 4.0σ discarded from variance update)
  └── Warm-up lifecycle state: INSUFFICIENT_DATA (n < 10) -> NORMAL / ANOMALOUS
          │
          ▼
[ Detection & Machine Learning (`aura/engine/service.py`, `model.py`) ]
  ├── Unsupervised Isolation Forest (3D feature vector: CPU, Net, Cam)
  └── Local Outlier Factor (LOF density estimator)
          │
          ▼
[ Multi-Signal Correlation Engine (`aura/engine/correlation.py`) ]
  ├── Sliding 60-second temporal window
  ├── Privacy Hardware + Outbound WAN burst correlation
  └── Anti-Double-Counting dampener for composite signals
          │
          ▼
[ Hardened Explainable Risk Engine (`aura/engine/risk_hardened.py`) ]
  ├── Deterministic 0–100 bounded scoring
  ├── Full contributor provenance (observed value, baseline, weight)
  └── Explicit degraded sensor state accounting
          │
          ▼
[ SQLite WAL Persistence (`aura/storage/sqlite.py`) ]
  ├── %LOCALAPPDATA%\AURA\aura.db
  └── Versioned migrations (telemetry, security_events, baseline_profiles, scan_runs)
          │
          ▼
[ Loopback REST API & WebSocket Transport (`aura/api/`) ]
  ├── Strict 127.0.0.1 binding
  ├── Ephemeral bootstrap token handshake + short-lived session tokens
  ├── Sliding-window rate limiting
  └── WebSocket tick streaming & real-time security event broadcasting
          │
          ▼
[ React + TypeScript Web Dashboard (`web/dist/`) ]
  ├── Static SPA served from local agent
  ├── Live Telemetry, Privacy Center, Security Events, Risk Intelligence
  └── Offline / Reconnect resilience & degraded health indicators
```

---

## 2. Dependency Baseline

### Python Dependencies (Runtime & Core)
| Package | Version Baseline | Purpose |
|---|---|---|
| `python` | >= 3.10 (tested on 3.14.3) | Core runtime environment |
| `fastapi` | >= 0.115.0 | High-performance local REST API |
| `uvicorn` | >= 0.34.0 | ASGI server bound to loopback |
| `pydantic` / `pydantic-settings` | >= 2.7.0 | Strictly typed contracts & validated configuration |
| `psutil` | >= 6.1.0 | OS & hardware telemetry probes |
| `scikit-learn` | >= 1.6.0 | Unsupervised Isolation Forest and LOF detection |
| `numpy` | >= 2.0.0 | Matrix transformations & feature scaling |
| `pandas` | >= 2.2.0 | Baseline CSV ingestion |
| `joblib` | >= 1.4.0 | Model artifact serialization |
| `opencv-python` / `sounddevice` | Optional / graceful | Hardware sentinel probes |

### Frontend Dependencies (Build & UI)
| Package | Version Baseline | Purpose |
|---|---|---|
| `react` / `react-dom` | ^19.0.0 | UI component library |
| `typescript` | ~5.7.2 | Strict compile-time typing (0 errors) |
| `vite` | ^6.2.0 | Frontend build bundler |
| `lucide-react` | ^1.16.0 | Design system iconography |
| `vitest` | ^3.0.7 | Frontend automated unit test runner |

---

## 3. Supported Windows Assumptions
1. **Operating System:** Windows 10 (Build 19041+) and Windows 11 (64-bit).
2. **Single Instance:** Win32 Named Mutex `Local\AURA_Privacy_Guardian_SingleInstance` (with lockfile fallback).
3. **Startup:** Windows Task Scheduler `AtLogon` task registered via `schtasks.exe` (HKCU Run key as policy fallback).
4. **Loopback Isolation:** REST & WebSocket services bind strictly to `127.0.0.1`. Remote network interfaces are denied.
5. **Least Privilege:** Runs standard user context without requiring Windows Administrator elevation for baseline operations.

---

## 4. Test Baseline & Quality Metrics
- **Python Backend Test Suite:** **71 / 71 tests passing (100%)**.
- **Frontend Test Suite:** **7 / 7 Vitest tests passing (100%)**.
- **TypeScript Strict Check:** **0 errors (`tsc --noEmit`)**.
- **Bytecode Compilation:** **100% clean (`python -m compileall`)**.
- **Legacy Compatibility:** `app.py` backward import confirmed.
- **Packaging:** PyInstaller onedir distribution and Inno Setup manifest verified.

---

## 5. Known Design Limitations & Privacy Boundaries
1. **Zero Content Sniffing:** AURA inspects socket metadata (IP, port, transfer rates, PID) but never intercepts or inspects plaintext packet payloads.
2. **Camera Privacy:** Video frames are never captured, recorded, or written to disk. The webcam probe queries device availability only.
3. **Microphone Privacy:** Audio waveforms are never recorded or transcribed. The sentinel inspects active CoreAudio stream session states.
4. **PID Resolution on System Services:** Windows OS security restricts querying process names for elevated system PIDs when AURA runs in standard user context; such processes are labeled `inaccessible` with `ConfidenceLevel.OBSERVED` without failing the scan cycle.
