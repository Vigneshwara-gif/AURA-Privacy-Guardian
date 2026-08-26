# Troubleshooting & Diagnostics

## Common Issues & Resolutions

### 1. Port 8787 Collision
- **Symptom:** Agent logs `Port 8787 is occupied. API disabled; engine continuing in DEGRADED mode.`
- **Resolution:** Check if another instance of AURA or another application is using port 8787. You can configure a custom port via `AURA_API__PORT=9001` in `.env` or environment variables.

### 2. Single-Instance Mutex Rejection
- **Symptom:** `Another instance of AURA agent is already running.`
- **Resolution:** AURA uses Win32 Named Mutex `Local\AURA_Privacy_Guardian_SingleInstance` to ensure only one monitoring daemon runs per user session. Check Task Manager for existing `aura.exe` processes.

### 3. Missing Webcam / Microphone Permissions
- **Symptom:** Camera / Microphone sensor status reports `DEGRADED` or `NOT_DETECTED`.
- **Resolution:** Ensure Windows Privacy Settings (`Settings -> Privacy & Security -> Camera / Microphone`) allow desktop applications to access device hardware status.

### 4. Running CLI Diagnostics
```powershell
python -m aura.cli.doctor
```
