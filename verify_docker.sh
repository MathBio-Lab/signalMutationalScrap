#!/bin/bash

echo "🚀 Verificando servicios Docker..."
echo ""

# Construir y levantar servicios
echo "📦 Construyendo y levantando servicios..."
docker compose up --build -d

echo ""
echo "⏳ Esperando 10 segundos para que los servicios inicien..."
sleep 10

echo ""
echo "📋 Estado de los servicios:"
docker compose ps

echo ""
echo "🔍 Logs de migraciones:"
docker compose logs signal_migrations

echo ""
echo "🏥 Verificando healthchecks:"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}"

echo ""
echo "🌐 Verificando API (debe responder en http://localhost:8000):"
curl -f http://localhost:8000/docs 2>/dev/null && echo "✅ API está respondiendo" || echo "❌ API no está respondiendo"

echo ""
echo "📊 Logs de la API (últimas 20 líneas):"
docker compose logs --tail=20 signal_api

echo ""
echo "✅ Verificación completa. Accede a http://localhost:8000/docs para ver la documentación de la API"
