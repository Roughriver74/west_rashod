"""
West Rashod - Bank Transactions Microservice
FastAPI application entry point
"""
import logging
from fastapi import FastAPI, Request
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
from app.api.v1.tasks import router as tasks_router
from app.api.v1.websocket import router as websocket_router
from app.api.v1.categorization_patterns import router as categorization_patterns_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Starting West Rashod API...")
    yield
    # Shutdown
    print("Shutting down West Rashod API...")


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

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
