#!/bin/bash
# Script de inicio rápido para la API REST

set -e

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Tiendita IA - API REST Multiagente             ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════╝${NC}\n"

# Verificar si existe .env
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠ Archivo .env no encontrado.${NC}"
    echo -e "${YELLOW}  Copiando .env.example a .env...${NC}\n"
    cp .env.example .env
    echo -e "${GREEN}✓ Archivo .env creado.${NC}"
    echo -e "${YELLOW}  Por favor edita .env con tus API keys antes de continuar.${NC}\n"
    exit 1
fi

# Cargar variables de entorno
export $(grep -v '^#' .env | xargs)

# Configuración de servidor
PORT=${API_PORT:-8000}
HOST=${API_HOST:-0.0.0.0}
RELOAD=${API_RELOAD:-true}

if [ "$RELOAD" = "true" ]; then
    RELOAD_FLAG="--reload"
else
    RELOAD_FLAG=""
fi

echo -e "${GREEN}✓ Servidor configurado: http://${HOST}:${PORT}${NC}"
echo -e "${GREEN}✓ Documentación: http://localhost:${PORT}/docs${NC}\n"

# Ejecutar API con uvicorn
echo -e "${BLUE}Iniciando servidor FastAPI...${NC}\n"
uv run uvicorn api:app --host $HOST --port $PORT $RELOAD_FLAG
