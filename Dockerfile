FROM python:3.12-slim

WORKDIR /app

# System libraries required for psycopg2 (source build) and SSH
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    openssh-client \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies before copying the rest of the code
# so this layer is cached as long as requirements.txt doesn't change
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Ensure the outputs directory exists (volume can be mounted over it)
RUN mkdir -p outputs

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "Home.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.headless=true"]
