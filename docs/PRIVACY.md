# AURA Privacy Model & Data Minimization Policy

## 1. What AURA Collects
- **Host Metrics:** CPU load percentage, RAM usage, Disk space, Inbound/Outbound network rates (KB/s).
- **Socket Metadata:** Local IP, local port, remote IP, remote port, connection status, associated process PID.
- **Hardware Status:** Active/Inactive state of camera and microphone devices.
- **Process Table:** Process ID (PID), process name, memory footprint.

## 2. What AURA NEVER Collects
- **NO Packet Content:** Plaintext HTTP headers, URL paths, file payloads, or TLS streams are NEVER inspected or captured.
- **NO Audio Recording:** Microphone waveforms are never recorded or transcribed.
- **NO Video Capture:** Webcam frames are never captured or saved to disk.
- **NO Keystroke / Clipboard Logging:** User input and clipboard buffers are completely ignored.
- **NO Cloud Telemetry:** Telemetry data NEVER leaves your computer. All processing and persistence are 100% local.

## 3. Storage & Retention
- All data is stored in a local SQLite database at `%LOCALAPPDATA%\AURA\data\aura.db`.
- Data retention is bounded by local storage limits and user-configurable cleanup policies.
