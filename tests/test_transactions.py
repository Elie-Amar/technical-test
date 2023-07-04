from datetime import date

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


@pytest.fixture
def deposit_transaction():
    return {
        "amount": 10.5,
        "type": "deposit",
        "date": date.today().strftime("%Y-%m-%d"),
    }


@pytest.fixture
def scheduled_withdrawal_transaction_may():
    return {
        "amount": 20,
        "type": "scheduled_withdrawal",
        "date": "2020-05-15",
    }

@pytest.fixture
def scheduled_withdrawal_transaction_april():
    return {
        "amount": 100,
        "type": "scheduled_withdrawal",
        "date": "2020-04-15",
    }

def test_hello():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_get_transactions():
    response = client.get("users/1/transactions")
    assert response.status_code == 200
    for transaction in response.json():
        assert transaction["user_id"] == 1


def test_get_transactions_not_existing_user():
    response = client.get("users/123/transactions")
    assert response.status_code == 200
    transaction = response.json()
    assert transaction == []


def test_get_existing_transaction():
    response = client.get("users/1/transactions/1")
    assert response.status_code == 200
    transaction = response.json()
    assert transaction["user_id"] == 1
    assert transaction["id"] == 1


def test_get_nonexisting_transaction():
    response = client.get("users/1/transactions/9999")
    assert response.status_code == 404


def test_get_transaction_nonexisting_user():
    response = client.get("users/999/transactions/1")
    assert response.status_code == 404


def test_create_transaction(deposit_transaction):
    response = client.post("users/2/transactions", json=deposit_transaction)
    assert response.status_code == 200
    transaction = response.json()
    assert transaction["user_id"] == 2
    assert transaction["amount"] == 10.5
    assert transaction["type"] == "deposit"
    assert transaction["date"] == date.today().isoformat()
    assert transaction["state"] == "pending"


def test_check_balance_not_existing_user():
    response = client.get("users/123/transactions/balance")
    assert response.status_code == 200
    balance = response.json()
    assert balance == {"balance": 0, "deadlines": {}}


def test_check_balance_zero_balance(scheduled_withdrawal_transaction_may, scheduled_withdrawal_transaction_april):
    response = client.get("users/1/transactions/balance")
    assert response.status_code == 200
    balance = response.json()
    assert balance == {
        "balance": 0,
        "deadlines": {
            "January 2020": {"due_amount": 20, "covered_amount": 20, "coverage_ratio": 100},
            "February 2020": {"due_amount": 28, "covered_amount": 28, "coverage_ratio": 100},
            "March 2020": {"due_amount": 20, "covered_amount": 20, "coverage_ratio": 100},
            "April 2020": {"due_amount": 300, "covered_amount": 17, "coverage_ratio": 6},
        },
    }

    # adding a withdraw on May => will append a line
    response = client.post("users/1/transactions", json=scheduled_withdrawal_transaction_may)
    response = client.get("users/1/transactions/balance")
    assert response.status_code == 200
    balance = response.json()
    assert balance == {
        "balance": 0,
        "deadlines": {
            "January 2020": {"due_amount": 20, "covered_amount": 20, "coverage_ratio": 100},
            "February 2020": {"due_amount": 28, "covered_amount": 28, "coverage_ratio": 100},
            "March 2020": {"due_amount": 20, "covered_amount": 20, "coverage_ratio": 100},
            "April 2020": {"due_amount": 300, "covered_amount": 17, "coverage_ratio":6},
            "May 2020": {"due_amount": 20, "covered_amount": 0, "coverage_ratio": 0},
        },
    }

    # adding a withdraw on April => will modify April line
    response = client.post("users/1/transactions", json=scheduled_withdrawal_transaction_april)
    response = client.get("users/1/transactions/balance")
    assert response.status_code == 200
    balance = response.json()
    print(balance)
    assert balance == {
        "balance": 0,
        "deadlines": {
            "January 2020": {"due_amount": 20, "covered_amount": 20, "coverage_ratio": 100},
            "February 2020": {"due_amount": 28, "covered_amount": 28, "coverage_ratio": 100},
            "March 2020": {"due_amount": 20, "covered_amount": 20, "coverage_ratio": 100},
            "April 2020": {"due_amount": 400, "covered_amount": 17, "coverage_ratio":4}, # changes here
            "May 2020": {"due_amount": 20, "covered_amount": 0, "coverage_ratio": 0},
        },
    }


def test_check_balance_positive_balance(scheduled_withdrawal_transaction_may):
    response = client.get("users/3/transactions/balance")
    assert response.status_code == 200
    balance = response.json()
    assert balance == {
        "balance": 30,
        "deadlines": {"February 2020": {"due_amount": 20, "covered_amount": 20, "coverage_ratio": 100}},
    }

    # withdraw 20 more => balance will be 10
    response = client.post("users/3/transactions", json=scheduled_withdrawal_transaction_may)
    response = client.get("users/3/transactions/balance")
    assert response.status_code == 200
    balance = response.json()
    assert balance == {
        "balance": 10,
        "deadlines": {
            "February 2020": {"due_amount": 20, "covered_amount": 20, "coverage_ratio": 100},
            "May 2020": {"due_amount": 20, "covered_amount": 20, "coverage_ratio": 100},
        },
    }
