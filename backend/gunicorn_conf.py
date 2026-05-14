bind = "0.0.0.0:8000"
worker_class = "uvicorn.workers.UvicornWorker"
workers = 2
timeout = 90
keepalive = 5
accesslog = "-"
errorlog = "-"

