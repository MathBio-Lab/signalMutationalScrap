FROM python:3.11-slim

WORKDIR /app

# instalar dependencias de sistema
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# copiar dependencias
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# copiar código fuente
COPY . .

CMD ["bash"]
