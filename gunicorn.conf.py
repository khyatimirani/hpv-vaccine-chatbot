"""
Gunicorn configuration for production deployment.

Reference: https://docs.gunicorn.org/en/stable/settings.html
"""

import multiprocessing

# ---------------------------------------------------------------------------
# Server socket
# ---------------------------------------------------------------------------
bind = "0.0.0.0:8000"

# ---------------------------------------------------------------------------
# Worker processes
# ---------------------------------------------------------------------------
# A safe starting point: 2 workers × CPU count + 1, capped at 9
workers = min(multiprocessing.cpu_count() * 2 + 1, 9)
worker_class = "sync"
timeout = 120
keepalive = 5

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
accesslog = "-"   # stdout
errorlog = "-"    # stderr
loglevel = "info"

# ---------------------------------------------------------------------------
# Process naming
# ---------------------------------------------------------------------------
proc_name = "hpv-vaccine-chatbot"
