FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV APP_HOME=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ curl git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR $APP_HOME

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Optional: install PostgreSQL vector support
RUN pip install pgvector psycopg2-binary

# Copy app source
COPY . .

# Create data directory
RUN mkdir -p data/vector_db

# Add non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app $APP_HOME
USER app

# Cloud Run expects port 8080
EXPOSE 8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Cloud Run uses $PORT environment variable
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
