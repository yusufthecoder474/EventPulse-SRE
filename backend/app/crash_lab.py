"""Explicit local/CI-only process fault hook. No HTTP endpoint is exposed."""
import os
import signal


def install_crash_handler():
    if os.getenv("ENABLE_PROCESS_CRASH_TEST") != "true":
        return False
    if os.getenv("APP_ENV", "local") != "local" or not hasattr(signal, "SIGUSR1"):
        raise RuntimeError("Process crash test requires local POSIX execution")

    def abrupt_exit(signum, frame):
        # Bypass cleanup to simulate abrupt process failure for Docker restart testing.
        os._exit(86)

    signal.signal(signal.SIGUSR1, abrupt_exit)
    return True
