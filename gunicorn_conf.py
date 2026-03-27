import os
import sys

is_render = any(k.startswith("RENDER") for k in os.environ.keys())

# Render sets PORT at runtime. For local/dev, fall back to 10000.
raw_port = os.environ.get("PORT")
port = (raw_port or "").strip()
if is_render and not port:
    raise RuntimeError("PORT env var is missing/empty on Render; cannot bind.")
if not port:
    port = "10000"
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
print(f"[gunicorn] PORT raw={raw_port!r} is_render={is_render}", file=sys.stderr, flush=True)
