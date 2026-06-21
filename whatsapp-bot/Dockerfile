FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todos os módulos
COPY bridge/ bridge/
COPY bot/ bot/

EXPOSE 3001

# Usar o webhook da Evolution API como entrypoint
CMD ["uvicorn", "bridge.evolution_webhook:app", "--host", "0.0.0.0", "--port", "3001"]
