"""Service for updating bank information in existing transactions."""
import logging
from typing import Dict, Tuple

from sqlalchemy.orm import Session

from app.db.models import BankTransaction
from app.services.odata_1c_client import OData1CClient

logger = logging.getLogger(__name__)


def load_all_bank_accounts(client: OData1CClient) -> Dict[str, Tuple[str, str]]:
    """
    Load all bank accounts from 1C into cache.

    Returns:
        Dict[account_number, Tuple[bank_name, bank_bik]]
    """
    logger.info("Loading bank accounts from 1C...")
    accounts_cache = {}

    try:
        skip = 0
        page_size = 100

        while True:
            response = client._make_request(
                method='GET',
                endpoint='Catalog_БанковскиеСчетаОрганизаций',
                params={
                    '$format': 'json',
                    '$expand': 'Банк',
                    '$top': page_size,
                    '$skip': skip
                }
            )

            results = response.get('value', [])

            if not results:
                break

            for account_data in results:
                account_number = account_data.get('НомерСчета')

                if not account_number:
                    continue

                # Get bank information
                bank_name = None
                bank_bik = None

                # From expanded data
                bank_data = account_data.get('Банк')
                if bank_data and isinstance(bank_data, dict):
                    bank_name = (
                        bank_data.get('Description') or
                        bank_data.get('Наименование') or
                        bank_data.get('НаименованиеПолное')
                    )
                    bank_bik = bank_data.get('Code') or bank_data.get('Код') or bank_data.get('БИК')

                # Fallback: data directly from account_data
                if not bank_name or not bank_bik:
                    bank_name = bank_name or account_data.get('НаименованиеБанка')
                    bank_bik = bank_bik or account_data.get('БИКБанка')

                if bank_name and bank_bik:
                    accounts_cache[account_number] = (
                        str(bank_name)[:500],
                        str(bank_bik)[:20]
                    )

            skip += page_size

        logger.info(f"Loaded {len(accounts_cache)} bank accounts from 1C")
        return accounts_cache

    except Exception as e:
        logger.error(f"Error loading bank accounts: {e}")
        return accounts_cache


def update_transactions_bank_info(db: Session, client: OData1CClient) -> Dict[str, int]:
    """
    Update bank information in all transactions without it.

    Returns:
        Dict with statistics: {'updated': int, 'errors': int, 'total': int}
    """
    logger.info("Starting bank information update in transactions...")

    try:
        # Get transactions without bank info
        transactions = db.query(BankTransaction).filter(
            BankTransaction.our_bank_name.is_(None),
            BankTransaction.account_number.isnot(None),
            BankTransaction.account_number != 'Касса'
        ).all()

        total = len(transactions)
        updated = 0
        errors = 0

        if total == 0:
            logger.info("No transactions need bank information update")
            return {'updated': 0, 'errors': 0, 'total': 0}

        logger.info(f"Found {total} transactions to update")

        # Load all bank accounts from 1C
        accounts_cache = load_all_bank_accounts(client)

        # Update transactions
        for transaction in transactions:
            account_number = transaction.account_number

            if account_number in accounts_cache:
                bank_name, bank_bik = accounts_cache[account_number]

                transaction.our_bank_name = bank_name
                transaction.our_bank_bik = bank_bik
                updated += 1
            else:
                logger.debug(f"Account {account_number} not found in 1C bank accounts")
                errors += 1

        # Commit changes
        db.commit()
        logger.info(f"Bank information update completed: updated={updated}, errors={errors}, total={total}")

        return {
            'updated': updated,
            'errors': errors,
            'total': total
        }

    except Exception as e:
        logger.error(f"Error updating bank information: {e}", exc_info=True)
        db.rollback()
        return {
            'updated': 0,
            'errors': 0,
            'total': 0,
            'error': str(e)
        }
