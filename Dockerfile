FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir "websockets>=12.0" "mcp[cli]>=1.27.0"

COPY scripts/ ./scripts/

ENTRYPOINT ["python", "scripts/mcp_server.py"]
