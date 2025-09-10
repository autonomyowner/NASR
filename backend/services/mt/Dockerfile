# Machine Translation Service Dockerfile
# Multi-stage build for efficient model loading and GPU optimization

FROM nvidia/cuda:11.8-devel-ubuntu20.04 as builder

# Install Python and build dependencies
RUN apt-get update && apt-get install -y \
    python3.9 \
    python3.9-dev \
    python3-pip \
    build-essential \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic link for python3
RUN ln -s /usr/bin/python3.9 /usr/bin/python

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM nvidia/cuda:11.8-runtime-ubuntu20.04

# Install Python runtime
RUN apt-get update && apt-get install -y \
    python3.9 \
    python3.9-distutils \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic link for python3
RUN ln -s /usr/bin/python3.9 /usr/bin/python

# Create app user for security
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.9/dist-packages /usr/local/lib/python3.9/dist-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app.py .
COPY requirements.txt .

# Create model cache directory
RUN mkdir -p /app/models && chown -R app:app /app/models

# Create glossaries directory
RUN mkdir -p /app/glossaries && chown -R app:app /app/glossaries

# Switch to app user
USER app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV MODEL_CACHE_DIR=/app/models
ENV HF_HOME=/app/models
ENV TRANSFORMERS_CACHE=/app/models

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Expose port
EXPOSE 8002

# Run the application
CMD ["python", "app.py"]