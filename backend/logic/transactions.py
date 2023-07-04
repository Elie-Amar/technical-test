from typing import List, Dict, Tuple

from backend.models import (
    Transaction,
    TransactionRow,
    TransactionState,
    TransactionType,
    Deadline,
    Balance,
)
from backend.models.interfaces import Database


def transactions(db: Database, user_id: int) -> List[TransactionRow]:
    """
    Returns all transactions of a user.
    """
    return [transaction for transaction in db.scan("transactions") if transaction.user_id == user_id]


def transaction(db: Database, user_id: int, transaction_id: int) -> TransactionRow:
    """
    Returns a given transaction of the user.
    """
    transaction = db.get("transactions", transaction_id)
    return transaction if transaction and transaction.user_id == user_id else None


def create_transaction(db: Database, user_id: int, transaction: Transaction) -> TransactionRow:
    """
    Creates a new transaction (adds an ID) and returns it.
    """
    if transaction.type in (TransactionType.DEPOSIT, TransactionType.REFUND):
        initial_state = TransactionState.PENDING
    elif transaction.type == TransactionType.SCHEDULED_WITHDRAWAL:
        initial_state = TransactionState.SCHEDULED
    else:
        raise ValueError(f"Invalid transaction type {transaction.type}")
    transaction_row = TransactionRow(user_id=user_id, **transaction.dict(), state=initial_state)
    return db.put("transactions", transaction_row)


def get_balance(db: Database, user_id: int) -> Balance:
    """
    Return the balance of payments of the user.

    Note: a deadline is a dict where the key is the month and year, and the value is:
    - the amount due
    - the amount covered by the current balance
    - the ratio (in percent, between 0 and 100) of coverage of the covered amount
    """
    trs: List[TransactionRow] = transactions(db, user_id)

    total_deposit, deadlines = _create_deadlines_and_sum_deposits(trs)

    final_balance, filled_deadlines = _distribute_deposit_to_deadlines(
        total_deposit,
        deadlines,
    )

    return Balance(balance=final_balance, deadlines=filled_deadlines)


def _create_deadlines_and_sum_deposits(
    transactions: List[TransactionRow],
) -> Tuple[int, Dict[str, Deadline]]:
    """
    Creates deadlines, sums up deposit amounts and write deadlines' due amounts
    """
    total_deposit: int = 0
    deadlines: Dict[str, Deadline] = {}
    for tra in transactions:
        # Calculate the month and year of the transaction
        month_year = tra.date.strftime("%B %Y")

        # Create a deadline object for the evaluated month in the transaction
        if month_year not in deadlines:
            deadlines[month_year] = Deadline()

        # Calculate the sum of each valid deposit
        if tra.type == TransactionType.DEPOSIT and tra.state == TransactionState.COMPLETED:
            total_deposit += tra.amount
        # Write due amounts for valid scheduled withdrawals and refunds
        elif (
            tra.type in (TransactionType.SCHEDULED_WITHDRAWAL, TransactionType.REFUND)
            and tra.state != TransactionState.FAILED
        ):
            deadlines[month_year].due_amount += tra.amount
    return total_deposit, deadlines


def _distribute_deposit_to_deadlines(
    deposit: int, deadlines: Dict[str, Deadline]
) -> Tuple[int, Dict[str, Deadline]]:
    """
    Distribute the total deposit amount into each deadline, until there is no more left
    """
    for deadline in deadlines.values():
        deadline.covered_amount = min(deposit, deadline.due_amount)
        deposit -= deadline.covered_amount

        if deadline.due_amount > 0:
            deadline.coverage_ratio = round(deadline.covered_amount / deadline.due_amount, 2) * 100

        # if there's no more deposit, no need to loop for next deadlines
        if deposit == 0:
            break
    return deposit, deadlines
