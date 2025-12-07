#!/bin/bash
# Test script to build Docker image locally with store location data
set -e

echo "🧪 Testing Docker build with store location data"

# Get project root (parent of python-ocr)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "📁 Project root: $PROJECT_ROOT"
echo "📁 Script dir: $SCRIPT_DIR"

# Prepare build context
echo ""
echo "📦 Preparing build context..."
cd "$SCRIPT_DIR"

# Copy store-scraper data
echo "  → Copying store location data..."
mkdir -p store-scraper-data
cp -r "$PROJECT_ROOT/store-scraper/data"/*.json store-scraper-data/
FILE_COUNT=$(ls -1 store-scraper-data/*.json 2>/dev/null | wc -l | tr -d ' ')
echo "  ✅ Copied $FILE_COUNT location files"

# List what we're including
echo ""
echo "📋 Build context contents:"
ls -lh store-scraper-data/

# Build the image
echo ""
echo "🏗️ Building Docker image..."
docker build -t receiptly-python-ocr:test .

# Verify the data is in the image
echo ""
echo "🔍 Verifying store location data in image..."
FILE_COUNT_IN_IMAGE=$(docker run --rm receiptly-python-ocr:test sh -c "ls -1 /app/store-scraper-data/*.json 2>/dev/null | wc -l" | tr -d ' ')
echo "  → Found $FILE_COUNT_IN_IMAGE files in /app/store-scraper-data/"

if [ "$FILE_COUNT_IN_IMAGE" -eq "$FILE_COUNT" ]; then
    echo "  ✅ All location files successfully copied to image!"
else
    echo "  ❌ File count mismatch: expected $FILE_COUNT, got $FILE_COUNT_IN_IMAGE"
    exit 1
fi

# Test running the container
echo ""
echo "🚀 Testing container startup..."
CONTAINER_ID=$(docker run -d -p 8001:8000 \
    -e AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="dummy" \
    -e AZURE_DOCUMENT_INTELLIGENCE_KEY="dummy" \
    receiptly-python-ocr:test)

echo "  → Container ID: ${CONTAINER_ID:0:12}"

# Wait for service to start
echo "  → Waiting for service to start..."
sleep 5

# Check health
if curl -f http://localhost:8001/health > /dev/null 2>&1; then
    echo "  ✅ Service is healthy!"
else
    echo "  ⚠️ Service health check failed (may need real Azure credentials)"
fi

# Check logs for store location data loading
echo ""
echo "📋 Container logs (last 30 lines):"
docker logs --tail 30 "$CONTAINER_ID"

# Cleanup
echo ""
echo "🧹 Cleaning up..."
docker stop "$CONTAINER_ID" > /dev/null
docker rm "$CONTAINER_ID" > /dev/null
rm -rf store-scraper-data
echo "  ✅ Cleanup complete"

echo ""
echo "✅ Docker build test completed successfully!"
echo ""
echo "💡 To run the image manually:"
echo "   docker run -p 8000:8000 \\"
echo "     -e AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT='your-endpoint' \\"
echo "     -e AZURE_DOCUMENT_INTELLIGENCE_KEY='your-key' \\"
echo "     receiptly-python-ocr:test"
