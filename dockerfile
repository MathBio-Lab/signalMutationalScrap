FROM python:3.11-slim

WORKDIR /app

# instalar dependencias de sistema para Playwright y PostgreSQL
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    # Dependencias para Playwright/Chromium
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# copiar dependencias
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# instalar navegadores de Playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# copiar código fuente
COPY . .

CMD ["bash"]
