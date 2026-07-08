#!/bin/bash
echo "============================================"
echo "   BalKawach CPMS - Docker Launcher (Linux)"
echo "============================================"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "[ERROR] Docker is not running."
    echo "[INFO] Please start Docker Desktop or the Docker daemon:"
    echo "       sudo systemctl start docker"
    exit 1
fi

echo "[INFO] Docker is running."
echo "[INFO] Building and starting services..."
echo "[INFO] First boot may take 10-15 minutes (model download)..."
echo ""

docker compose up --build -d

echo ""
echo "============================================"
echo "   Services are starting up..."
echo "============================================"
echo ""
echo "   Frontend:       http://localhost:9122"
echo "   Backend API:    http://localhost:9120"
echo "   Transcription:  http://localhost:9121"
echo ""
echo "   docker compose logs -f    — view logs"
echo "   docker compose down       — stop"
echo "   docker compose down -v    — stop + remove data"
echo "============================================"
