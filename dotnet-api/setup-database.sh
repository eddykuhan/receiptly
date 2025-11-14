#!/bin/bash
# Database setup script for Receiptly

set -e

echo "=========================================="
echo "  Receiptly Database Setup"
echo "=========================================="
echo ""

# Check if PostgreSQL is accessible via Docker
echo "Checking PostgreSQL connection..."
if docker ps | grep -q postgres; then
    echo "✓ PostgreSQL container is running"
else
    echo "❌ PostgreSQL container not found"
    echo ""
    echo "To start PostgreSQL:"
    echo "  docker run --name receiptly-postgres \\"
    echo "    -e POSTGRES_PASSWORD=postgres \\"
    echo "    -e POSTGRES_DB=receiptly_db \\"
    echo "    -p 5432:5432 \\"
    echo "    -d postgres:15"
    echo ""
    exit 1
fi

echo ""

# Apply migrations
echo "Applying EF Core migrations..."
dotnet ef database update \
  --project src/Receiptly.Infrastructure/Receiptly.Infrastructure.csproj \
  --startup-project src/Receiptly.API/Receiptly.API.csproj

echo ""
echo "=========================================="
echo "✓ Database setup complete!"
echo "=========================================="
echo ""
echo "Database: receiptly_db"
echo "Tables created: receipts, items"
echo ""
echo "To verify, run:"
echo "  psql -h localhost -U postgres -d receiptly_db -c '\dt'"
echo ""
