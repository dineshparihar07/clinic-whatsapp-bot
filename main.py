from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import logging
import sys
from dotenv import load_dotenv

load_dotenv()

from api.webhook import router as webhook_router
from api.cron import router as cron_router
from lib.db import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Clinic WhatsApp Bot",
    version="0.1.0",
    description="Automated appointment booking system for clinics via WhatsApp"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(webhook_router, prefix="/api", tags=["webhook"])
app.include_router(cron_router, prefix="/api", tags=["cron"])

@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("🚀 Clinic WhatsApp Bot Starting")
    logger.info("=" * 60)

    # Check environment variables
    required_vars = ["WHATSAPP_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "GEMINI_API_KEY", "DATABASE_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.warning(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
    else:
        logger.info("✅ All required environment variables configured")

    # Initialize database
    try:
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        raise

    logger.info("=" * 60)
    logger.info("✅ Bot ready to receive messages!")
    logger.info("=" * 60)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "service": "Clinic WhatsApp Bot",
            "version": "0.1.0"
        }
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return JSONResponse(
        status_code=200,
        content={
            "message": "Clinic WhatsApp Bot API",
            "version": "0.1.0",
            "endpoints": {
                "webhook": "/api/webhook (GET for verification, POST for messages)",
                "reminders": "/api/cron/reminders (POST to trigger reminders)",
                "waiting_list": "/api/cron/backfill-waiting-list (POST to process waiting list)",
                "health": "/health"
            }
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 3000))
    env = os.getenv("ENV", "development")

    logger.info(f"Starting server on port {port} (ENV: {env})")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info" if env == "production" else "debug"
    )
