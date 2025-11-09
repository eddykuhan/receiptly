from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import ocr
from .core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Receiptly OCR Service",
    description="API for processing receipt images using OCR",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

# Include routers
app.include_router(
    ocr.router,
    prefix=settings.API_PREFIX + "/ocr",
    tags=["OCR"]
)

@app.get("/")
async def root():
    return {
        "message": "Receiptly OCR Service is running",
        "version": "1.0.0",
        "docs_url": "/docs"
    }