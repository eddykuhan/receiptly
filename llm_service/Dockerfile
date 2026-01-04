# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Copy shared library first
COPY shared-lib /shared-lib

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Install shared library from local path
RUN pip install --no-cache-dir --user /shared-lib

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Expose the port the app runs on
EXPOSE 8500

# Health check
HEALTHCHECK --interval=1h --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8500/docs').read()" || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8500"]
