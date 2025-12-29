"""
West Поток (West Potok) - Bank Transactions Microservice
FastAPI application entry point
"""
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import traceback

from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
from app.db.session import engine
from app.db.models import Base

# Import routers
from app.api.v1.auth import router as auth_router
from app.api.v1.bank_transactions import router as bank_transactions_router
from app.api.v1.business_operation_mappings import router as mappings_router
from app.api.v1.categories import router as categories_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.contractors import router as contractors_router
from app.api.v1.users import router as users_router
from app.api.v1.sync_1c import router as sync_1c_router
from app.api.v1.sync_settings import router as sync_settings_router
from app.api.v1.expenses import router as expenses_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.websocket import router as websocket_router
from app.api.v1.categorization_patterns import router as categorization_patterns_router

# Fin module router
from app.modules.fin.api.router import router as fin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Starting West Поток API...")

    # Start sync scheduler
    from app.services.sync_scheduler import sync_scheduler
    sync_scheduler.start()
    logger.info("Sync scheduler started")

    yield

    # Shutdown
    print("Shutting down West Поток API...")

    # Stop sync scheduler
    sync_scheduler.stop()
    logger.info("Sync scheduler stopped")

    # Shutdown task manager
    from app.services.background_tasks import task_manager
    task_manager.shutdown()
    logger.info("Task manager shut down")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Bank Transactions Microservice - независимый сервис для учета банковских операций",
    version="1.0.0",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler to ensure CORS headers are always present
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions with proper CORS headers."""
    if settings.DEBUG:
        print(f"Unhandled exception: {exc}")
        traceback.print_exc()

    # Get the origin from the request
    origin = request.headers.get("origin")

    # Create response
    response = JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An error occurred"
        }
    )

    # Add CORS headers explicitly if origin is in allowed list
    if origin and origin in settings.cors_origins_list:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"

    return response


# HTTPException handler to ensure CORS headers on HTTP errors (403, 404, etc.)
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper CORS headers."""
    if settings.DEBUG:
        print(f"HTTP exception: {exc.status_code} - {exc.detail}")

    # Get the origin from the request
    origin = request.headers.get("origin")

    # Create response
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

    # Add CORS headers explicitly if origin is in allowed list
    if origin and origin in settings.cors_origins_list:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"

    return response


# Health check
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "west-rashod",
        "version": "1.0.0"
    }


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "West Rashod API",
        "docs": "/docs",
        "health": "/health"
    }


# Include routers with API prefix
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(bank_transactions_router, prefix=settings.API_PREFIX)
app.include_router(expenses_router, prefix=settings.API_PREFIX)
app.include_router(analytics_router, prefix=settings.API_PREFIX)
app.include_router(mappings_router, prefix=settings.API_PREFIX)
app.include_router(categories_router, prefix=settings.API_PREFIX)
app.include_router(organizations_router, prefix=settings.API_PREFIX)
app.include_router(contractors_router, prefix=settings.API_PREFIX)
app.include_router(users_router, prefix=settings.API_PREFIX)
app.include_router(sync_1c_router, prefix=settings.API_PREFIX)
app.include_router(sync_settings_router, prefix=settings.API_PREFIX)
app.include_router(tasks_router, prefix=settings.API_PREFIX)
app.include_router(websocket_router, prefix=settings.API_PREFIX)
app.include_router(categorization_patterns_router, prefix=settings.API_PREFIX)

# Fin module (Financial Data Warehouse)
app.include_router(fin_router, prefix=f"{settings.API_PREFIX}/fin", tags=["Fin Module"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
