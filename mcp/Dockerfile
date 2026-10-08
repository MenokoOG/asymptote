# Asymptote MCP server: cloud/self-hosted image.
# Build:  docker build -t asymptote-mcp -f mcp/Dockerfile .
# Run  :  docker run -e ASYMPTOTE_TRANSPORT=streamable-http -p 8000:8000 asymptote-mcp
FROM python:3.12-slim

WORKDIR /app

# Engine (asymptote.py, agent_tool.py) + the mcp/ subfolder.
COPY . /app

RUN pip install --no-cache-dir -r mcp/requirements.txt

# Default to an HTTP transport so the container is reachable as a service.
ENV ASYMPTOTE_TRANSPORT=streamable-http
EXPOSE 8000

CMD ["python", "mcp/server.py"]
