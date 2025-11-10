#!/bin/bash

# Receiptly Services Shutdown Script
# This script stops both Python OCR and .NET API services

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}       Receiptly Services Shutdown Script        ${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Function to kill process on port
kill_port() {
    local port=$1
    local service=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo -e "${YELLOW}Stopping $service on port $port...${NC}"
        lsof -ti:$port | xargs kill -9 2>/dev/null
        sleep 1
        
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
            echo -e "${RED}✗ Failed to stop $service${NC}"
        else
            echo -e "${GREEN}✓ $service stopped${NC}"
        fi
    else
        echo -e "${YELLOW}$service is not running${NC}"
    fi
}

# Stop services by port
echo -e "${YELLOW}Stopping services...${NC}"
echo ""

kill_port 8000 "Python OCR Service"
kill_port 5188 ".NET API"

echo ""

# Stop services by PID if .service-pids file exists
if [ -f "$SCRIPT_DIR/.service-pids" ]; then
    echo -e "${YELLOW}Stopping services by PID...${NC}"
    
    while IFS= read -r pid; do
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${YELLOW}Killing process $pid...${NC}"
            kill -9 $pid 2>/dev/null || true
        fi
    done < "$SCRIPT_DIR/.service-pids"
    
    rm "$SCRIPT_DIR/.service-pids"
    echo -e "${GREEN}✓ PID file removed${NC}"
fi

echo ""
echo -e "${BLUE}==================================================${NC}"
echo -e "${GREEN}All services stopped${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""
