# Receiptly Service Management Scripts

This directory contains shell scripts to manage the Receiptly services (Python OCR and .NET API).

## Scripts

### 🚀 `start-services.sh`
Starts both Python OCR and .NET API services.

**Usage:**
```bash
./start-services.sh
```

**What it does:**
1. Checks and kills any existing processes on ports 8000 and 5188
2. Starts Python OCR service (port 8000)
3. Starts .NET API (port 5188)
4. Verifies both services are running
5. Saves process IDs to `.service-pids`
6. Displays service URLs and documentation links

**Output:**
- Logs: `logs/python-ocr.log` and `logs/dotnet-api.log`
- PIDs: `.service-pids`

---

### 🛑 `stop-services.sh`
Stops all running Receiptly services.

**Usage:**
```bash
./stop-services.sh
```

**What it does:**
1. Kills processes on ports 8000 and 5188
2. Kills processes by saved PIDs (if `.service-pids` exists)
3. Removes `.service-pids` file

---

### 📊 `check-services.sh`
Checks the status of all Receiptly services.

**Usage:**
```bash
./check-services.sh
```

**What it shows:**
- Whether each service is running
- Port numbers
- Process IDs
- HTTP response status
- Quick links to documentation
- Log file locations

---

## Prerequisites

### Python OCR Service
- Python 3.9+
- Virtual environment created in `python-ocr/venv`
- `.env` file in `python-ocr/` with Azure credentials

### .NET API
- .NET 8.0 SDK
- User secrets configured with AWS credentials:
  ```bash
  dotnet user-secrets set "AWS:AccessKeyId" "your-key" --project dotnet-api/src/Receiptly.API/Receiptly.API.csproj
  dotnet user-secrets set "AWS:SecretAccessKey" "your-secret" --project dotnet-api/src/Receiptly.API/Receiptly.API.csproj
  dotnet user-secrets set "AWS:S3BucketName" "your-bucket" --project dotnet-api/src/Receiptly.API/Receiptly.API.csproj
  dotnet user-secrets set "AWS:Region" "ap-southeast-1" --project dotnet-api/src/Receiptly.API/Receiptly.API.csproj
  ```

---

## Quick Start

1. **First time setup:**
   ```bash
   # Setup Python environment
   cd python-ocr
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env  # Edit .env with your credentials
   cd ..

   # Setup .NET user secrets
   dotnet user-secrets set "AWS:AccessKeyId" "your-key" --project dotnet-api/src/Receiptly.API/Receiptly.API.csproj
   # ... (set other secrets)
   ```

2. **Start services:**
   ```bash
   ./start-services.sh
   ```

3. **Check status:**
   ```bash
   ./check-services.sh
   ```

4. **Stop services:**
   ```bash
   ./stop-services.sh
   ```

---

## Service URLs

| Service | URL | Documentation |
|---------|-----|---------------|
| Python OCR | http://localhost:8000 | http://localhost:8000/docs |
| .NET API | http://localhost:5188 | http://localhost:5188/swagger |

---

## Troubleshooting

### Services won't start

1. **Check logs:**
   ```bash
   tail -f logs/python-ocr.log
   tail -f logs/dotnet-api.log
   ```

2. **Verify ports are free:**
   ```bash
   lsof -i :8000
   lsof -i :5188
   ```

3. **Check prerequisites:**
   - Python: `python3 --version`
   - .NET: `dotnet --version`
   - Virtual env: `ls -la python-ocr/venv`
   - User secrets: `dotnet user-secrets list --project dotnet-api/src/Receiptly.API/Receiptly.API.csproj`

### Services start but don't respond

1. **Check health endpoints:**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:5188/health
   ```

2. **Check environment variables:**
   - Python: `cat python-ocr/.env`
   - .NET: `dotnet user-secrets list --project dotnet-api/src/Receiptly.API/Receiptly.API.csproj`

### Port already in use

The start script automatically kills existing processes, but if that fails:
```bash
# Find process using port
lsof -i :8000  # or :5188

# Kill process
kill -9 <PID>
```

---

## Notes

- Scripts are designed for **local development** on macOS/Linux
- Services run in the background with output redirected to log files
- Process IDs are saved to `.service-pids` for easy cleanup
- Both `.service-pids` and `logs/` are gitignored

---

## Docker Alternative

If you prefer to use Docker:
```bash
docker-compose up --build
```

See `DOCKER.md` for Docker setup instructions.
