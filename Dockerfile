FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir .
ENV PORT=8080 LOCUST_WORKSPACE_ENV=production LOCUST_WORKSPACE_ROOT=/data
VOLUME ["/data"]
EXPOSE 8080
CMD ["sh", "-c", "test -n \"$LOCUST_WORKSPACE_API_KEY\" && exec gunicorn --bind 0.0.0.0:${PORT} --workers 2 'locust_templates.workspace_api:create_workspace_app()'"]
