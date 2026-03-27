import os
import sys

# Render sets PORT at runtime; fall back to 10000 for local/dev.
port = os.environ.get("PORT") or "10000"
bind = f"0.0.0.0:{port}"

# Ensure bind/worker boot logs show up in Render logs.
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info")
accesslog = "-"
errorlog = "-"
capture_output = True

# Render commonly sets WEB_CONCURRENCY automatically; default to 1 for small instances.
workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))

print(f"[gunicorn] bind={bind} (PORT env {'set' if os.environ.get('PORT') else 'missing'})", file=sys.stderr, flush=True)
