FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copiar pyproject.toml primeiro pra instalar deps
COPY pyproject.toml .
COPY README.md .

# Instalar dependências
RUN pip install --no-cache-dir . 2>/dev/null || true

# Copiar código fonte
COPY src/ src/

# Instalar o pacoto em modo editável
RUN pip install --no-cache-dir -e "." 2>/dev/null || pip install --no-cache-dir .

EXPOSE 8000

CMD ["python", "-m", "nfe_brasil.server", "--transport", "http", "--port", "8000"]
