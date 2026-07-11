# Stage 1: Build Next.js frontend
FROM --platform=linux/amd64 node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Final Python production image
FROM --platform=linux/amd64 python:3.11-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend
WORKDIR /app

# Install basic system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements file and install dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend application files (including pre-trained models)
COPY backend /app/backend

# Copy static frontend HTML/JS/CSS assets from Stage 1 builder
COPY --from=frontend-builder /app/frontend/out /app/frontend/out

# Copy entrypoint script and make it executable (normalizing line endings)
COPY entrypoint.sh /app/entrypoint.sh
RUN sed -i 's/\r$//' /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Declare volume mounts for input tasks and output results for batch processing
VOLUME ["/input", "/output"]

# Expose port 7860 (Hugging Face Spaces default container port)
EXPOSE 7860

# Set entrypoint and default launch target command
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["web"]
