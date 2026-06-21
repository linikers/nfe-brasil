FROM python:3.12-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependências Python
COPY pyproject.toml .
RUN pip install --no-cache-dir -e "." 2>/dev/null || pip install --no-cache-dir .

# Copiar código fonte
COPY src/ src/

EXPOSE 8000

CMD ["python", "-m", "nfe_brasil.server", "--transport", "http", "--port", "8000"]
