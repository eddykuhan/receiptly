#!/bin/bash

# Receiptly Services Startup Script
# This script starts both Python OCR and .NET API services

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}       Receiptly Services Startup Script         ${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    echo -e "${YELLOW}Killing process on port $port...${NC}"
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
    sleep 1
}

# Check and kill existing processes
echo -e "${YELLOW}Checking for existing processes...${NC}"
if check_port 8000; then
    echo -e "${YELLOW}Port 8000 (Python OCR) is in use${NC}"
    kill_port 8000
fi

if check_port 5188; then
    echo -e "${YELLOW}Port 5188 (.NET API) is in use${NC}"
    kill_port 5188
fi

echo ""

# Start Python OCR Service
echo -e "${GREEN}[1/2] Starting Python OCR Service...${NC}"
echo -e "${BLUE}----------------------------------------------${NC}"

cd "$SCRIPT_DIR/python-ocr"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found in python-ocr directory${NC}"
    echo -e "${YELLOW}Please create .env file with Azure credentials${NC}"
    exit 1
fi

# Start Python service in background
echo -e "${GREEN}Starting uvicorn server on port 8000...${NC}"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > "$SCRIPT_DIR/logs/python-ocr.log" 2>&1 &
PYTHON_PID=$!

# Wait for Python service to start
echo -e "${YELLOW}Waiting for Python OCR to start...${NC}"
for i in {1..30}; do
    if check_port 8000; then
        echo -e "${GREEN}✓ Python OCR started successfully (PID: $PYTHON_PID)${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ Python OCR failed to start${NC}"
        echo -e "${YELLOW}Check logs at: logs/python-ocr.log${NC}"
        exit 1
    fi
    sleep 1
done

echo ""

# Start .NET API
echo -e "${GREEN}[2/2] Starting .NET API...${NC}"
echo -e "${BLUE}----------------------------------------------${NC}"

cd "$SCRIPT_DIR/dotnet-api"

# Check if user secrets are configured
echo -e "${YELLOW}Checking user secrets...${NC}"
SECRET_COUNT=$(dotnet user-secrets list --project src/Receiptly.API/Receiptly.API.csproj 2>/dev/null | wc -l)
if [ $SECRET_COUNT -lt 4 ]; then
    echo -e "${RED}Warning: User secrets not fully configured${NC}"
    echo -e "${YELLOW}Run: dotnet user-secrets set \"AWS:AccessKeyId\" \"your-key\"${NC}"
fi

# Build the solution
echo -e "${GREEN}Building .NET solution...${NC}"
dotnet build Receiptly.sln --configuration Debug > "$SCRIPT_DIR/logs/dotnet-build.log" 2>&1
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Build failed${NC}"
    echo -e "${YELLOW}Check logs at: logs/dotnet-build.log${NC}"
    kill $PYTHON_PID
    exit 1
fi

# Start .NET API in background
echo -e "${GREEN}Starting .NET API on port 5188...${NC}"
dotnet run --project src/Receiptly.API/Receiptly.API.csproj > "$SCRIPT_DIR/logs/dotnet-api.log" 2>&1 &
DOTNET_PID=$!

# Wait for .NET API to start
echo -e "${YELLOW}Waiting for .NET API to start...${NC}"
for i in {1..30}; do
    if check_port 5188; then
        echo -e "${GREEN}✓ .NET API started successfully (PID: $DOTNET_PID)${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ .NET API failed to start${NC}"
        echo -e "${YELLOW}Check logs at: logs/dotnet-api.log${NC}"
        kill $PYTHON_PID
        exit 1
    fi
    sleep 1
done

echo ""
echo -e "${BLUE}==================================================${NC}"
echo -e "${GREEN}✓ All services started successfully!${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""
echo -e "${YELLOW}Services:${NC}"
echo -e "  Python OCR:  ${GREEN}http://localhost:8000${NC} (PID: $PYTHON_PID)"
echo -e "  .NET API:    ${GREEN}http://localhost:5188${NC} (PID: $DOTNET_PID)"
echo ""
echo -e "${YELLOW}Documentation:${NC}"
echo -e "  Python Docs: ${BLUE}http://localhost:8000/docs${NC}"
echo -e "  .NET Swagger:${BLUE}http://localhost:5188/swagger${NC}"
echo ""
echo -e "${YELLOW}Logs:${NC}"
echo -e "  Python:      ${BLUE}tail -f logs/python-ocr.log${NC}"
echo -e "  .NET:        ${BLUE}tail -f logs/dotnet-api.log${NC}"
echo ""
echo -e "${YELLOW}Process IDs saved to: ${BLUE}.service-pids${NC}"
echo "$PYTHON_PID" > "$SCRIPT_DIR/.service-pids"
echo "$DOTNET_PID" >> "$SCRIPT_DIR/.service-pids"
echo ""
echo -e "${RED}To stop all services, run: ${BLUE}./stop-services.sh${NC}"
echo ""
