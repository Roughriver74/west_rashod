#!/usr/bin/env python3
"""
Script to import fin module data from local XLSX files.

Usage:
    python scripts/import_fin_data.py /path/to/xlsx/directory

Example:
    python scripts/import_fin_data.py /Users/evgenijsikunov/projects/west/west_fin/west-west_fin/xls
"""
import sys
import os
import logging
from pathlib import Path

# Add the backend app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.modules.fin.services.importer import FinDataImporter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def import_xlsx_files(directory: str, clear_existing: bool = True):
    """Import all xlsx files from a directory."""
    dir_path = Path(directory)

    if not dir_path.exists():
        logger.error(f"Directory not found: {directory}")
        return False

    # Find all xlsx files
    xlsx_files = list(dir_path.glob("*.xlsx"))

    if not xlsx_files:
        logger.warning(f"No xlsx files found in: {directory}")
        return False

    logger.info(f"Found {len(xlsx_files)} xlsx files:")
    for f in xlsx_files:
        logger.info(f"  - {f.name}")

    # Sort files for proper import order (receipts first, then expenses, then details)
    def sort_key(path):
        name = path.name.lower()
        if "postuplenie" in name or "поступление" in name:
            return 0  # Receipts first
        elif "rasshifrovka" in name or "расшифровка" in name:
            return 2  # Details last
        elif "spisanie" in name or "списание" in name:
            return 1  # Expenses second
        return 3

    xlsx_files.sort(key=sort_key)

    logger.info("Files will be imported in order:")
    for f in xlsx_files:
        logger.info(f"  - {f.name}")

    # Create DB session
    db = SessionLocal()

    try:
        importer = FinDataImporter(db)

        # Clear existing data if requested
        if clear_existing:
            logger.info("Clearing existing data...")
            importer.clear_existing_data()

        # Import each file
        success_count = 0
        fail_count = 0

        for xlsx_file in xlsx_files:
            logger.info(f"Importing: {xlsx_file.name}")
            try:
                if importer.import_file(str(xlsx_file)):
                    success_count += 1
                    logger.info(f"  ✓ Success: {xlsx_file.name}")
                else:
                    fail_count += 1
                    logger.error(f"  ✗ Failed: {xlsx_file.name}")
            except Exception as e:
                fail_count += 1
                logger.error(f"  ✗ Error importing {xlsx_file.name}: {e}")

        logger.info(f"\nImport Summary:")
        logger.info(f"  Total files: {len(xlsx_files)}")
        logger.info(f"  Successful: {success_count}")
        logger.info(f"  Failed: {fail_count}")

        return fail_count == 0

    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nDefault: importing from west_fin xls directory")
        directory = "/Users/evgenijsikunov/projects/west/west_fin/west-west_fin/xls"
    else:
        directory = sys.argv[1]

    print(f"\nImporting fin data from: {directory}")
    success = import_xlsx_files(directory)

    sys.exit(0 if success else 1)
