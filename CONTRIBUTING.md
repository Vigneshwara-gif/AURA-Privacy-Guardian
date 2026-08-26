# Contributing to AURA Privacy Guardian

We welcome contributions! To maintain security, reliability, and privacy guarantees, please follow these guidelines.

## Development Workflow
1. Fork the repository and create a feature branch.
2. Ensure all Python code is strictly typed and adheres to standard PEP 8 formatting.
3. Ensure all frontend code passes TypeScript strict checks (`npm run typecheck`).
4. Run automated tests before submitting a PR:
   ```powershell
   python -m pytest
   python -m compileall aura packaging tests
   cd web && npm test && npm run build
   ```
5. Ensure zero privacy violations: do not add packet payload sniffing, keystroke capture, or off-device network telemetry.
