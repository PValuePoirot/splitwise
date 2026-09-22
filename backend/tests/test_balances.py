"""Tests for balances computation and debt simplification."""
from __future__ import annotations

from decimal import Decimal

from app.services.balances import UserBalance, simplify_debts


def test_simplify_debts_simple():
    # Alice is owed 100, Bob owes 100
    balances = [
        UserBalance(user_id=1, name="Alice", balance=Decimal("100")),
        UserBalance(user_id=2, name="Bob", balance=Decimal("-100")),
    ]
    debts = simplify_debts(balances)
    assert len(debts) == 1
    assert debts[0].from_user_id == 2
    assert debts[0].to_user_id == 1
    assert debts[0].amount == Decimal("100")


def test_simplify_debts_three_way():
    # Alice +100, Bob -60, Carol -40
    balances = [
        UserBalance(user_id=1, name="Alice", balance=Decimal("100")),
        UserBalance(user_id=2, name="Bob", balance=Decimal("-60")),
        UserBalance(user_id=3, name="Carol", balance=Decimal("-40")),
    ]
    debts = simplify_debts(balances)
    total_paid = sum((d.amount for d in debts), Decimal("0"))
    assert total_paid == Decimal("100")
    # Bob pays 60 to Alice, Carol pays 40 to Alice
    by_from = {d.from_user_id: d for d in debts}
    assert by_from[2].to_user_id == 1
    assert by_from[2].amount == Decimal("60")
    assert by_from[3].to_user_id == 1
    assert by_from[3].amount == Decimal("40")


def test_simplify_debts_chain():
    # Alice +50, Bob +30, Carol -80 (Carol pays Alice 50 and Bob 30)
    balances = [
        UserBalance(user_id=1, name="Alice", balance=Decimal("50")),
        UserBalance(user_id=2, name="Bob", balance=Decimal("30")),
        UserBalance(user_id=3, name="Carol", balance=Decimal("-80")),
    ]
    debts = simplify_debts(balances)
    total = sum((d.amount for d in debts), Decimal("0"))
    assert total == Decimal("80")


def test_simplify_debts_all_zero():
    balances = [
        UserBalance(user_id=1, name="Alice", balance=Decimal("0")),
        UserBalance(user_id=2, name="Bob", balance=Decimal("0")),
    ]
    assert simplify_debts(balances) == []


def test_balances_after_expense(client, group_with_members, user_a):
    login = client.post("/auth/login", json={"email": user_a.email, "password": "password123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    gid = group_with_members.id
    # Alice pays 90, split equally among 3 -> each owes 30
    client.post(
        f"/groups/{gid}/expenses",
        json={
            "description": "Dinner",
            "total_amount": "90.00",
            "split_type": "equal",
            "participants": [
                {"user_id": user_a.id, "paid_share": "90.00", "owed_share": "30.00"},
                {"user_id": group_with_members.members[1].user_id, "paid_share": "0", "owed_share": "30.00"},
                {"user_id": group_with_members.members[2].user_id, "paid_share": "0", "owed_share": "30.00"},
            ],
        },
        headers=headers,
    )
    resp = client.get(f"/groups/{gid}/balances", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    by_user = {b["user_id"]: Decimal(b["balance"]) for b in data["balances"]}
    assert by_user[user_a.id] == Decimal("60.00")
    assert by_user[group_with_members.members[1].user_id] == Decimal("-30.00")
    assert by_user[group_with_members.members[2].user_id] == Decimal("-30.00")
    # Simplified debts: each debtor pays Alice 30
    assert len(data["simplified_debts"]) == 2


def test_balances_after_settlement_zeroes_out(client, group_with_members, user_a):
    login = client.post("/auth/login", json={"email": user_a.email, "password": "password123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    gid = group_with_members.id
    bob_id = group_with_members.members[1].user_id
    # Bob owes Alice 30 (Alice paid 90, split 3 ways)
    client.post(
        f"/groups/{gid}/expenses",
        json={
            "description": "Dinner",
            "total_amount": "90.00",
            "split_type": "equal",
            "participants": [
                {"user_id": user_a.id, "paid_share": "90.00", "owed_share": "30.00"},
                {"user_id": bob_id, "paid_share": "0", "owed_share": "30.00"},
                {"user_id": group_with_members.members[2].user_id, "paid_share": "0", "owed_share": "30.00"},
            ],
        },
        headers=headers,
    )
    # Bob settles 30 to Alice
    client.post(
        f"/groups/{gid}/settlements",
        json={"from_user_id": bob_id, "to_user_id": user_a.id, "amount": "30.00"},
        headers=headers,
    )
    resp = client.get(f"/groups/{gid}/balances", headers=headers)
    by_user = {b["user_id"]: Decimal(b["balance"]) for b in resp.json()["balances"]}
    assert by_user[bob_id] == Decimal("0")
