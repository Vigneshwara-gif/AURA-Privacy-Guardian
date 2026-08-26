# Installation & Deployment Guide

## System Requirements
- **OS:** Windows 10 (64-bit Build 19041+) or Windows 11.
- **Hardware:** 2+ CPU cores, 4 GB RAM, 200 MB free disk space.
- **Privileges:** Standard interactive user account (Administrator elevation not required).

## Installation Methods

### Method 1: Production Standalone Package
1. Download `aura-installer.exe` or the `aura-agent` distribution folder.
2. Run installer or launch `aura.exe`.
3. AURA will register a Task Scheduler `AtLogon` task for automatic background monitoring.
4. Access the web dashboard at `http://127.0.0.1:8787`.

### Method 2: Development / Source Checkout
1. Install Python 3.10+ and Node.js 20+.
2. Run `pip install -r requirements.txt`.
3. In `web/`, run `npm install && npm run build`.
4. Launch `python -m aura.entrypoints.agent_main`.

## Uninstallation & Data Retention
- Standard uninstallation removes application binaries from `Program Files\AURA`.
- Telemetry logs and historical database records in `%LOCALAPPDATA%\AURA` are preserved by default to prevent accidental data loss. To perform a complete purge, delete the `%LOCALAPPDATA%\AURA` folder manually.
