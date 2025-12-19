"""
Application Constants

This file contains all hardcoded values that are used across the application.
"""

# ============================================================================
# AI & MACHINE LEARNING THRESHOLDS
# ============================================================================

# Transaction Classifier - Keyword Matching Scores
AI_KEYWORD_EXACT_SCORE = 10  # Exact match
AI_KEYWORD_START_SCORE = 8  # Starts with keyword
AI_KEYWORD_CONTAINS_SCORE = 5  # Contains keyword

# Transaction Classifier - Confidence Calculation
AI_MIN_SCORE_THRESHOLD = 5  # Minimum score to consider
AI_CONFIDENCE_MIN_BASE = 0.7  # Base confidence minimum
AI_SCORE_TO_CONFIDENCE_DIVISOR = 50  # Divisor for score-to-confidence conversion
AI_CONFIDENCE_MAX_CAP = 0.95  # Maximum confidence cap

# Transaction Classifier - Historical Data
AI_HISTORICAL_CONFIDENCE = 0.95  # Confidence from historical matches
AI_MIN_HISTORICAL_TRANSACTIONS = 2  # Minimum transactions for historical analysis

# Transaction Classifier - Name-based Matching
AI_NAME_BASED_CONFIDENCE_MULTIPLIER = 0.8  # Confidence multiplier for name matches

# Transaction Classifier - Default Confidences by Type
AI_DEFAULT_CREDIT_CONFIDENCE = 0.6  # Default for CREDIT transactions
AI_DEFAULT_DEBIT_CONFIDENCE = 0.5  # Default for DEBIT transactions

# Transaction Classifier - Boosts
AI_CREDIT_TYPE_BOOST = 0.1  # Boost for CREDIT transactions
AI_DEBIT_TYPE_BOOST = 0.05  # Boost for DEBIT transactions
AI_MATCH_COUNT_MULTIPLIER = 0.1  # Multiplier per matching keyword

# Bank Transaction Import - Auto-categorization Thresholds
AI_HIGH_CONFIDENCE_THRESHOLD = 0.9  # Auto-assign category if confidence > 90%
AI_MEDIUM_CONFIDENCE_THRESHOLD = 0.5  # Needs review if confidence < 50%

# Regular Payment Detection
REGULAR_PAYMENT_PATTERN_THRESHOLD = 0.3  # 30% variation threshold for pattern detection

# Transaction Confidence Thresholds (for analytics/reporting)
CONFIDENCE_HIGH_THRESHOLD = 0.9  # High confidence (≥90%)
CONFIDENCE_MEDIUM_THRESHOLD = 0.7  # Medium confidence (70-89%)
CONFIDENCE_LOW_THRESHOLD = 0.5  # Low confidence (50-69%)

# ============================================================================
# PAGINATION & BATCH SIZES
# ============================================================================

# Default Pagination
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000

# Bank Transactions Pagination
DEFAULT_BANK_TX_PAGE_SIZE = 50
MAX_BANK_TX_PAGE_SIZE = 500

# Batch Processing
SYNC_BATCH_SIZE = 100  # Batch size for 1C sync operations
IMPORT_BATCH_SIZE = 100  # Batch size for imports
MAX_IMPORT_ROWS = 10000  # Maximum rows for import

# Preview settings
PREVIEW_SAMPLE_ROWS = 5  # Number of rows to show in import preview

# ============================================================================
# API TIMEOUTS
# ============================================================================

# OData 1C Integration
ODATA_REQUEST_TIMEOUT = 30  # Default HTTP request timeout (seconds)
ODATA_CONNECTION_TIMEOUT = 30  # Connection timeout
ODATA_GET_REQUEST_TIMEOUT = 10  # GET request timeout

# ============================================================================
# BUSINESS LOGIC
# ============================================================================

# Business Operation Mapping
DEFAULT_MAPPING_CONFIDENCE = 0.98  # Default confidence for operation mappings

# Month Validation
MIN_MONTH = 1
MAX_MONTH = 12
