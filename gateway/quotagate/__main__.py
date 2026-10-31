"""Run QuotaGate via uvicorn."""
import os
import sys

from uvicorn import run

from quotagate.main import app

if __name__ == "__main__":
    port = int(os.environ.get("QUOTAGATE_PORT", 8766))
    host = os.environ.get("QUOTAGATE_HOST", "127.0.0.1")
    reload = os.environ.get("QUOTAGATE_RELOAD", "0") == "1"
    run(app, host=host, port=port, reload=reload)