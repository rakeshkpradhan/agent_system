# Gunicorn configuration for production deployment

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = min(multiprocessing.cpu_count() * 2 + 1, 8)
worker_class = "gthread" 
threads = 2
worker_connections = 1000
timeout = 300
keepalive = 2

# Restart workers after this many requests
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
access_log_format = '%%(h)s %%(l)s %%(u)s %%(t)s "%%(r)s" %%(s)s %%(b)s "%%(f)s" "%%(a)s" %%(D)s'

# Process naming
proc_name = "agentic-compliance-api"

# Server mechanics
preload_app = True
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Enable stats
statsd_host = None
statsd_prefix = ""
