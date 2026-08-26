"""
Production Entry Point for aura-agent.exe (Headless Background Daemon).
"""

from __future__ import annotations

import asyncio
import os
import sys

from aura.agent.daemon import AuraAgentDaemon


def main() -> int:
    """Launch the autonomous background daemon."""
    daemon = AuraAgentDaemon()

    async def _run() -> None:
        await daemon.start(run_api=True)
        try:
            while daemon.is_running:
                await asyncio.sleep(1.0)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            await daemon.stop()

    try:
        asyncio.run(_run())
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"FATAL: AURA Agent Daemon crashed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
