FROM python:3.11-slim

# Install Chromium dependencies
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates fonts-wqy-zenhei \
    libnss3 libatk-bridge2.0-0 libdrm2 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libasound2 libpango-1.0-0 \
    libcairo2 libcups2 libxss1 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .

# Install Playwright browsers
RUN uv run playwright install chromium

CMD ["uv", "run", "python", "worker.py"]
