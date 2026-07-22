#!/bin/bash
# Railway start script - locust web UI for performance testing
# PORT is set by Railway, default 8089 for local testing
PORT="${PORT:-8089}"
exec locust -f src/locust_templates/api_load.py --web-host 0.0.0.0 --web-port "$PORT"
