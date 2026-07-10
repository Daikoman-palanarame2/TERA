# Target linux/amd64 platform explicitly
FROM --platform=linux/amd64 python:3.11-slim

# Set environment variables for clean container output
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend

# Set working directory inside container
WORKDIR /app

# Install basic system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend application files (including pre-trained models in app/models)
COPY backend /app/backend

# Copy entrypoint script and make it executable (normalizing CRLF -> LF endings)
COPY entrypoint.sh /app/entrypoint.sh
RUN sed -i 's/\r$//' /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Declare volume mounts for input tasks and output results
VOLUME ["/input", "/output"]

# Set startup execution command
ENTRYPOINT ["/app/entrypoint.sh"]
