import os

bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# Render commonly sets WEB_CONCURRENCY automatically; default to 1 for small instances.
workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))

