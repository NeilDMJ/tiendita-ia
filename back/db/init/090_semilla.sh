#!/bin/bash
# Carga los datos de ejemplo (SINTÉTICOS) si CARGAR_SEMILLA=1. Solo corre al crear la BD.
set -euo pipefail

if [ "${CARGAR_SEMILLA:-1}" != "1" ]; then
  echo "semilla: omitida (CARGAR_SEMILLA=${CARGAR_SEMILLA:-})"
  exit 0
fi

echo "semilla: cargando catálogo de /datos/catalogo.csv y datos de ejemplo…"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /semilla/semilla.sql
