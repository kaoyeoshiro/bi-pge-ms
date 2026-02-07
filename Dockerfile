# ============================================
# Estágio 1 — Build do frontend (Node)
# ============================================
FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ============================================
# Estágio 2 — Backend + arquivos estáticos
# ============================================
FROM python:3.13-slim

WORKDIR /app/backend

# Dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependências Python
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Código do backend
COPY backend/ ./

# Arquivos estáticos do frontend (gerados no estágio 1)
COPY --from=frontend-build /app/frontend/dist ./static

# Variáveis de ambiente padrão
ENV PYTHONUNBUFFERED=1
ENV PORT=8001

EXPOSE ${PORT}

# Iniciar com uvicorn (roda a partir de /app/backend, onde src/ está acessível)
CMD ["sh", "-c", "python -m uvicorn src.main:app --host 0.0.0.0 --port ${PORT}"]
