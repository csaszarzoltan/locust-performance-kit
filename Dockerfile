FROM python:3.11-slim

WORKDIR /app

# Copy dependency manifest first for layer caching
COPY pyproject.toml .

# Copy source code
COPY src/ src/

# Install package and dependencies
RUN pip install --no-cache-dir .

EXPOSE ${PORT}

CMD ["sh", "-c", "locust -f src/locust_templates/api_load.py --web-host 0.0.0.0 --web-port ${PORT:-8089}"]
