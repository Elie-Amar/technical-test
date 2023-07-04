from typing import Dict
from datetime import date
from enum import Enum

from pydantic import BaseModel


class TransactionType(str, Enum):
    DEPOSIT: str = "deposit"
    SCHEDULED_WITHDRAWAL: str = "scheduled_withdrawal"
    REFUND: str = "refund"


class TransactionState(str, Enum):
    SCHEDULED: str = "scheduled"
    PENDING: str = "pending"
    COMPLETED: str = "completed"
    FAILED: str = "failed"


class Row(BaseModel):
    id: int = 0  # id is overwritten by the database upon insertion


class User(BaseModel):
    name: str
    email: str


class UserRow(Row, User):
    pass


class Transaction(BaseModel):
    amount: float
    date: date
    type: TransactionType


class TransactionRow(Row, Transaction):
    user_id: int
    state: TransactionState


class Deadline(BaseModel):
    due_amount: int = 0
    covered_amount: int = 0
    coverage_ratio: int = 0


class Balance(BaseModel):
    balance: int
    deadlines: Dict[str, Deadline]
