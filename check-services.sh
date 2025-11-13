#!/bin/bash

# Receiptly Services Status Check Script

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}         Receiptly Services Status Check          ${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""

# Function to check service status
check_service() {
    local port=$1
    local name=$2
    local url=$3
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        local pid=$(lsof -ti:$port)
        echo -e "${GREEN}✓ $name is running${NC}"
        echo -e "  Port: ${BLUE}$port${NC}"
        echo -e "  PID:  ${BLUE}$pid${NC}"
        echo -e "  URL:  ${BLUE}$url${NC}"
        
        # Try to get response
        if command -v curl &> /dev/null; then
            local status=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
            if [ "$status" = "200" ] || [ "$status" = "307" ]; then
                echo -e "  Status: ${GREEN}Responding ($status)${NC}"
            else
                echo -e "  Status: ${YELLOW}Running but not responding ($status)${NC}"
            fi
        fi
    else
        echo -e "${RED}✗ $name is not running${NC}"
        echo -e "  Port: ${BLUE}$port${NC}"
        echo -e "  Status: ${RED}Not listening${NC}"
    fi
    echo ""
}

# Check Python OCR Service
check_service 8000 "Python OCR Service" "http://localhost:8000/health"

# Check .NET API
check_service 5188 ".NET API" "http://localhost:5188/health"

# Check if PID file exists
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
if [ -f "$SCRIPT_DIR/.service-pids" ]; then
    echo -e "${YELLOW}Saved PIDs:${NC}"
    cat "$SCRIPT_DIR/.service-pids" | while read pid; do
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "  PID $pid: ${GREEN}Running${NC}"
        else
            echo -e "  PID $pid: ${RED}Not running${NC}"
        fi
    done
    echo ""
fi

echo -e "${BLUE}==================================================${NC}"
echo -e "${YELLOW}Quick links:${NC}"
echo -e "  Python Docs: ${BLUE}http://localhost:8000/docs${NC}"
echo -e "  .NET Swagger:${BLUE}http://localhost:5188/swagger${NC}"
echo ""
echo -e "${YELLOW}View logs:${NC}"
echo -e "  ${BLUE}tail -f logs/python-ocr.log${NC}"
echo -e "  ${BLUE}tail -f logs/dotnet-api.log${NC}"
echo -e "${BLUE}==================================================${NC}"
