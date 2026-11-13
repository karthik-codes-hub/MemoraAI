import os

bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
threads = int(os.getenv("PYTHON_GET_THREADS", "4"))
timeout = 120
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = "info"
