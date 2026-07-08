#!/bin/bash
echo "==================================================="
echo "Starting BalKawach in Docker"
echo "==================================================="
echo ""

# Navigate to the script's directory so it can be run from anywhere
cd "$(dirname "$0")"

# Check if Docker is installed and running
if ! command -v docker &> /dev/null
then
    echo "[ERROR] Docker is not installed or not running in your PATH."
    echo "Please download and install Docker Desktop for Mac:"
    echo "https://www.docker.com/products/docker-desktop/"
    echo ""
    echo "Press [Enter] to exit..."
    read -r
    exit 1
fi

# Check if docker daemon is reachable
if ! docker info > /dev/null 2>&1; then
    echo "[ERROR] Docker Desktop is installed but not running."
    echo "Please open the Docker application from your Applications folder, wait for it to start, and try again."
    echo ""
    echo "Press [Enter] to exit..."
    read -r
    exit 1
fi

echo "Building and starting containers (this may take a few minutes the first time)..."
docker compose up --build -d

echo ""
echo "==================================================="
echo "Containers started successfully!"
echo ""
echo "Frontend   : http://localhost:9122"
echo "Backend API: http://localhost:9123"
echo "==================================================="
echo ""

# Give it a few seconds to boot up before opening the browser
sleep 3
open http://localhost:9122
