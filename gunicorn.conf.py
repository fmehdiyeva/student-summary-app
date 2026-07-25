# Gunicorn configuration — auto-loaded by `gunicorn app:app`, so it applies
# even when the platform's start command doesn't pass these flags.
#
# The free-tier AI model can take 20-40 seconds to respond, which exceeds
# gunicorn's default 30s timeout and kills the request. Raise it, and use a
# few threads so one slow request doesn't block the whole site.
timeout = 120
workers = 1
threads = 4
