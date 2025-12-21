"""Expense matching service for linking bank transactions to expenses."""
from typing import List, Tuple, Optional
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db.models import (
    BankTransaction, Expense, ExpenseStatusEnum,
    BankTransactionTypeEnum, BankTransactionStatusEnum
)
from app.schemas.expense import MatchingSuggestion


class ExpenseMatchingService:
    """Service for matching bank transactions to expense requests."""

    # Matching weights
    AMOUNT_WEIGHT = 40.0      # Weight for amount match
    DATE_WEIGHT = 20.0        # Weight for date proximity
    COUNTERPARTY_WEIGHT = 30.0  # Weight for counterparty match
    PURPOSE_WEIGHT = 10.0     # Weight for payment purpose match

    # Thresholds
    AMOUNT_TOLERANCE = 0.05   # 5% tolerance for amount matching
    DATE_TOLERANCE_DAYS = 14  # Days tolerance for date matching
    MIN_SCORE_THRESHOLD = 30.0  # Minimum score to consider a match

    def __init__(self, db: Session):
        self.db = db

    def find_matching_expenses(
        self,
        transaction: BankTransaction,
        threshold: float = None,
        limit: int = 5
    ) -> List[MatchingSuggestion]:
        """
        Find potential matching expenses for a bank transaction.

        Args:
            transaction: The bank transaction to match
            threshold: Minimum matching score (default: MIN_SCORE_THRESHOLD)
            limit: Maximum number of suggestions to return

        Returns:
            List of matching suggestions sorted by score
        """
        if threshold is None:
            threshold = self.MIN_SCORE_THRESHOLD

        # Only match DEBIT transactions (outgoing payments)
        if transaction.transaction_type != BankTransactionTypeEnum.DEBIT:
            return []

        # Get candidate expenses
        candidates = self._get_candidate_expenses(transaction)

        suggestions = []
        for expense in candidates:
            score, reasons = self.calculate_matching_score(transaction, expense)

            if score >= threshold:
                remaining = expense.amount - (expense.amount_paid or Decimal("0"))

                suggestions.append(MatchingSuggestion(
                    expense_id=expense.id,
                    expense_number=expense.number,
                    expense_title=expense.title,
                    expense_amount=expense.amount,
                    expense_date=expense.request_date,
                    expense_category_id=expense.category_id,
                    expense_category_name=expense.category_rel.name if expense.category_rel else None,
                    expense_contractor_name=expense.contractor_name,
                    expense_contractor_inn=expense.contractor_inn,
                    expense_status=expense.status.value,
                    remaining_amount=remaining,
                    matching_score=score,
                    match_reasons=reasons
                ))

        # Sort by score descending and limit
        suggestions.sort(key=lambda x: x.matching_score, reverse=True)
        return suggestions[:limit]

    def _get_candidate_expenses(self, transaction: BankTransaction) -> List[Expense]:
        """Get candidate expenses for matching."""
        # Base query - only approved or partially paid expenses
        query = self.db.query(Expense).filter(
            Expense.is_active == True,
            Expense.status.in_([
                ExpenseStatusEnum.APPROVED,
                ExpenseStatusEnum.PARTIALLY_PAID
            ])
        )

        # Filter by amount range (transaction amount should be <= expense remaining amount)
        # Allow some tolerance
        min_amount = transaction.amount * Decimal(str(1 - self.AMOUNT_TOLERANCE))
        max_amount = transaction.amount * Decimal(str(1 + self.AMOUNT_TOLERANCE)) * 2  # Allow partial payments

        query = query.filter(
            or_(
                # Exact amount match
                and_(
                    Expense.amount >= min_amount,
                    Expense.amount <= max_amount
                ),
                # Partial payment possible
                (Expense.amount - Expense.amount_paid) >= min_amount
            )
        )

        # Filter by date range
        date_from = transaction.transaction_date - timedelta(days=self.DATE_TOLERANCE_DAYS * 3)
        query = query.filter(Expense.request_date >= date_from)

        # Prioritize by counterparty INN if available
        if transaction.counterparty_inn:
            query = query.filter(
                or_(
                    Expense.contractor_inn == transaction.counterparty_inn,
                    Expense.contractor_inn.is_(None)
                )
            )

        return query.limit(50).all()

    def calculate_matching_score(
        self,
        transaction: BankTransaction,
        expense: Expense
    ) -> Tuple[float, List[str]]:
        """
        Calculate matching score between transaction and expense.

        Returns:
            Tuple of (score, list of match reasons)
        """
        score = 0.0
        reasons = []

        # 1. Amount matching
        remaining_amount = expense.amount - (expense.amount_paid or Decimal("0"))
        amount_score, amount_reason = self._score_amount_match(
            transaction.amount,
            expense.amount,
            remaining_amount
        )
        score += amount_score
        if amount_reason:
            reasons.append(amount_reason)

        # 2. Date proximity
        date_score, date_reason = self._score_date_proximity(
            transaction.transaction_date,
            expense.request_date,
            expense.due_date
        )
        score += date_score
        if date_reason:
            reasons.append(date_reason)

        # 3. Counterparty matching
        cp_score, cp_reason = self._score_counterparty_match(
            transaction.counterparty_inn,
            transaction.counterparty_name,
            expense.contractor_inn,
            expense.contractor_name
        )
        score += cp_score
        if cp_reason:
            reasons.append(cp_reason)

        # 4. Payment purpose matching
        purpose_score, purpose_reason = self._score_purpose_match(
            transaction.payment_purpose,
            expense.payment_purpose,
            expense.title,
            expense.number
        )
        score += purpose_score
        if purpose_reason:
            reasons.append(purpose_reason)

        return round(score, 2), reasons

    def _score_amount_match(
        self,
        tx_amount: Decimal,
        exp_amount: Decimal,
        remaining_amount: Decimal
    ) -> Tuple[float, Optional[str]]:
        """Score amount matching."""
        # Exact match with remaining amount
        if abs(tx_amount - remaining_amount) <= remaining_amount * Decimal(str(self.AMOUNT_TOLERANCE)):
            return self.AMOUNT_WEIGHT, f"Сумма совпадает с остатком ({remaining_amount:,.2f})"

        # Exact match with total amount
        if abs(tx_amount - exp_amount) <= exp_amount * Decimal(str(self.AMOUNT_TOLERANCE)):
            return self.AMOUNT_WEIGHT * 0.9, f"Сумма совпадает с заявкой ({exp_amount:,.2f})"

        # Partial payment (transaction amount < remaining)
        if tx_amount < remaining_amount:
            ratio = float(tx_amount / remaining_amount)
            if ratio >= 0.5:
                return self.AMOUNT_WEIGHT * 0.7, f"Частичная оплата ({ratio*100:.0f}%)"
            elif ratio >= 0.25:
                return self.AMOUNT_WEIGHT * 0.5, f"Частичная оплата ({ratio*100:.0f}%)"
            else:
                return self.AMOUNT_WEIGHT * 0.3, f"Малая частичная оплата ({ratio*100:.0f}%)"

        return 0.0, None

    def _score_date_proximity(
        self,
        tx_date: date,
        exp_request_date: date,
        exp_due_date: Optional[date]
    ) -> Tuple[float, Optional[str]]:
        """Score date proximity."""
        # Check due date first
        if exp_due_date:
            days_diff = abs((tx_date - exp_due_date).days)
            if days_diff == 0:
                return self.DATE_WEIGHT, "Оплата в срок"
            elif days_diff <= 3:
                return self.DATE_WEIGHT * 0.9, f"Оплата близко к сроку (±{days_diff} дн.)"
            elif days_diff <= 7:
                return self.DATE_WEIGHT * 0.7, f"Оплата в пределах недели от срока"

        # Check request date
        days_after_request = (tx_date - exp_request_date).days
        if 0 <= days_after_request <= 3:
            return self.DATE_WEIGHT * 0.8, "Оплата сразу после заявки"
        elif 0 <= days_after_request <= 7:
            return self.DATE_WEIGHT * 0.6, "Оплата в течение недели"
        elif 0 <= days_after_request <= 14:
            return self.DATE_WEIGHT * 0.4, "Оплата в течение 2 недель"
        elif days_after_request > 14:
            return self.DATE_WEIGHT * 0.2, "Оплата позже 2 недель"

        return 0.0, None

    def _score_counterparty_match(
        self,
        tx_inn: Optional[str],
        tx_name: Optional[str],
        exp_inn: Optional[str],
        exp_name: Optional[str]
    ) -> Tuple[float, Optional[str]]:
        """Score counterparty matching."""
        # INN match is the strongest signal
        if tx_inn and exp_inn and tx_inn == exp_inn:
            return self.COUNTERPARTY_WEIGHT, f"ИНН контрагента совпадает ({tx_inn})"

        # Name similarity check
        if tx_name and exp_name:
            tx_name_lower = tx_name.lower().strip()
            exp_name_lower = exp_name.lower().strip()

            # Exact name match
            if tx_name_lower == exp_name_lower:
                return self.COUNTERPARTY_WEIGHT * 0.9, "Название контрагента совпадает"

            # Partial name match
            tx_words = set(tx_name_lower.split())
            exp_words = set(exp_name_lower.split())
            common_words = tx_words.intersection(exp_words)

            if len(common_words) >= 2:
                return self.COUNTERPARTY_WEIGHT * 0.6, "Частичное совпадение названия"
            elif len(common_words) >= 1 and len(common_words[0] if common_words else '') > 3:
                return self.COUNTERPARTY_WEIGHT * 0.3, "Есть общие слова в названии"

        return 0.0, None

    def _score_purpose_match(
        self,
        tx_purpose: Optional[str],
        exp_purpose: Optional[str],
        exp_title: str,
        exp_number: str
    ) -> Tuple[float, Optional[str]]:
        """Score payment purpose matching."""
        if not tx_purpose:
            return 0.0, None

        tx_purpose_lower = tx_purpose.lower()

        # Check if expense number mentioned in purpose
        if exp_number and exp_number.lower() in tx_purpose_lower:
            return self.PURPOSE_WEIGHT, f"Номер заявки в назначении ({exp_number})"

        # Check expense title in purpose
        if exp_title:
            title_words = [w for w in exp_title.lower().split() if len(w) > 3]
            matching_words = sum(1 for w in title_words if w in tx_purpose_lower)
            if matching_words >= 2:
                return self.PURPOSE_WEIGHT * 0.8, "Тема заявки в назначении"
            elif matching_words >= 1:
                return self.PURPOSE_WEIGHT * 0.5, "Частичное совпадение назначения"

        # Check expense purpose in transaction purpose
        if exp_purpose:
            purpose_words = [w for w in exp_purpose.lower().split() if len(w) > 3]
            matching_words = sum(1 for w in purpose_words if w in tx_purpose_lower)
            if matching_words >= 2:
                return self.PURPOSE_WEIGHT * 0.7, "Назначение платежа совпадает"

        return 0.0, None

    def link_transaction_to_expense(
        self,
        transaction_id: int,
        expense_id: int,
        matching_score: Optional[float] = None
    ) -> bool:
        """
        Link a transaction to an expense.

        Returns:
            True if successful, raises exception otherwise
        """
        transaction = self.db.query(BankTransaction).filter(
            BankTransaction.id == transaction_id,
            BankTransaction.is_active == True
        ).first()

        if not transaction:
            raise ValueError("Transaction not found")

        expense = self.db.query(Expense).filter(
            Expense.id == expense_id,
            Expense.is_active == True
        ).first()

        if not expense:
            raise ValueError("Expense not found")

        # Link transaction
        transaction.expense_id = expense_id
        transaction.matching_score = Decimal(str(matching_score)) if matching_score else None
        transaction.status = BankTransactionStatusEnum.MATCHED

        # Update expense paid amount
        expense.amount_paid = (expense.amount_paid or Decimal("0")) + transaction.amount

        # Update expense status
        if expense.amount_paid >= expense.amount:
            expense.status = ExpenseStatusEnum.PAID
            expense.payment_date = transaction.transaction_date
        elif expense.amount_paid > 0:
            expense.status = ExpenseStatusEnum.PARTIALLY_PAID

        self.db.commit()
        return True

    def auto_match_transactions(
        self,
        threshold: float = 70.0,
        limit: int = 100
    ) -> List[dict]:
        """
        Automatically match unlinked transactions with high confidence.

        Returns:
            List of matched pairs with scores
        """
        # Get unlinked debit transactions
        transactions = self.db.query(BankTransaction).filter(
            BankTransaction.is_active == True,
            BankTransaction.expense_id.is_(None),
            BankTransaction.transaction_type == BankTransactionTypeEnum.DEBIT,
            BankTransaction.status.in_([
                BankTransactionStatusEnum.NEW,
                BankTransactionStatusEnum.CATEGORIZED,
                BankTransactionStatusEnum.NEEDS_REVIEW
            ])
        ).limit(limit).all()

        matched = []
        for tx in transactions:
            suggestions = self.find_matching_expenses(tx, threshold=threshold, limit=1)

            if suggestions and suggestions[0].matching_score >= threshold:
                suggestion = suggestions[0]

                self.link_transaction_to_expense(
                    tx.id,
                    suggestion.expense_id,
                    suggestion.matching_score
                )

                matched.append({
                    "transaction_id": tx.id,
                    "expense_id": suggestion.expense_id,
                    "expense_number": suggestion.expense_number,
                    "score": suggestion.matching_score,
                    "reasons": suggestion.match_reasons
                })

        return matched
