#!/bin/bash

echo "🧪 Script de Prueba - Integración Scraper con Celery"
echo "======================================================"
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Verificar que los servicios estén corriendo
echo -e "${YELLOW}1. Verificando servicios Docker...${NC}"
docker compose ps

echo ""
echo -e "${YELLOW}2. Subiendo CSV de prueba...${NC}"

# Subir el archivo de prueba
RESPONSE=$(curl -s -X POST http://localhost:8000/ \
  -F "file=@app/uploads/test2.csv")

echo "$RESPONSE" | python3 -m json.tool

# Extraer work_id del response
WORK_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('work_id', ''))")

if [ -z "$WORK_ID" ]; then
    echo -e "${RED}❌ Error: No se pudo obtener work_id${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Work ID obtenido: $WORK_ID${NC}"

echo ""
echo -e "${YELLOW}3. Esperando 5 segundos para que la tarea inicie...${NC}"
sleep 5

echo ""
echo -e "${YELLOW}4. Verificando estado de la tarea...${NC}"
curl -s -X POST http://localhost:8000/check/ \
  -d "work_id=$WORK_ID" | grep -o 'Estado: [A-Z]*'

echo ""
echo ""
echo -e "${YELLOW}5. Logs del Celery Worker (últimas 30 líneas):${NC}"
docker compose logs --tail=30 signal_celery_worker

echo ""
echo ""
echo -e "${GREEN}✅ Prueba completada${NC}"
echo ""
echo "Para verificar el estado manualmente:"
echo "  1. Visita: http://localhost:8000/check/"
echo "  2. Ingresa el Work ID: $WORK_ID"
echo ""
echo "Para ver logs en tiempo real:"
echo "  docker compose logs -f signal_celery_worker"
