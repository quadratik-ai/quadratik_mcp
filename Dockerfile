FROM python:3.12-slim

WORKDIR /app

# Install system dependencies if needed (e.g., curl for health checks)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server code
COPY . .

# Stdio servers don't "listen" on a port, but for SSE or marketplace 
# testing, we expose a placeholder
EXPOSE 8000

# Default to HTTP transport for deployed environments
ENV MCP_TRANSPORT=http

# Command to run the server
CMD ["python", "main.py"]