"""
Main router for Fin module.
Aggregates all sub-routers for the financial data warehouse.
"""
from fastapi import APIRouter

from app.modules.fin.api import receipts, expenses, ftp_import, references, analytics, adjustments

router = APIRouter()

# Include sub-routers
router.include_router(receipts.router, prefix="/receipts", tags=["Fin - Receipts"])
router.include_router(expenses.router, prefix="/expenses", tags=["Fin - Expenses"])
router.include_router(ftp_import.router, prefix="/import", tags=["Fin - FTP Import"])
router.include_router(references.router, prefix="/references", tags=["Fin - References"])
router.include_router(analytics.router, prefix="/analytics", tags=["Fin - Analytics"])
router.include_router(adjustments.router, prefix="/adjustments", tags=["Fin - Adjustments"])
