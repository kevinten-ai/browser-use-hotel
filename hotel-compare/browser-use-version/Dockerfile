FROM python:3.11-slim

# Install base system dependencies for Chromium + fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates fonts-wqy-zenhei \
    libnss3 libatk-bridge2.0-0 libdrm2 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libasound2 libpango-1.0-0 \
    libcairo2 libcups2 libxss1 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy dependency manifests first for better layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Install Playwright browsers and their system deps BEFORE copying source code
# so that code changes do not invalidate this heavy layer (~150 MB).
RUN uv run playwright install chromium && \
    uv run playwright install-deps chromium && \
    rm -rf /var/lib/apt/lists/*

# Copy application code (honors .dockerignore)
COPY . .

CMD ["uv", "run", "python", "worker.py"]
