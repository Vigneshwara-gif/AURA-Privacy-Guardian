# Security Policy for AURA Privacy Guardian

## Supported Versions
| Version | Supported |
|---|---|
| 2.0.x | Yes |
| < 2.0 | No |

## Reporting a Vulnerability
If you discover a security vulnerability in AURA, please report it responsibly by creating a private security advisory on GitHub or contacting the maintainers. Do not open public issues for sensitive security defects.

## Security Architecture Principles
- **Least Privilege:** AURA runs in the interactive user context without requiring administrator elevation.
- **Local Isolation:** REST and WebSocket transports bind strictly to `127.0.0.1`.
- **Ephemeral Authentication:** API interactions require single-use ephemeral bootstrap exchange and short-lived session tokens.
- **Parameterized Persistence:** All SQLite storage interactions use parameterized queries to prevent SQL injection.
